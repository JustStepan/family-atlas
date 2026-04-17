from datetime import datetime, timedelta

from sqlalchemy import select, func
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    DocumentAttributeAudio,
    DocumentAttributeVideo,
)
from telethon.tl.types import PeerChannel

from src.config import settings
from src.database.engine import ensure_db_initialized, get_db
from src.database.models import LocalRawMessages
from src.database.utils import get_or_create
from src.logger import logger


THREAD_MAPS = {
    2: "diary",
    4: "calendar",
    6: "notes",
    8: "task",
}


def detect_msg_type(msg) -> str | None:
    if not msg.media:
        return "text" if msg.message else None
    if isinstance(msg.media, MessageMediaPhoto):
        return "photo"
    if isinstance(msg.media, MessageMediaDocument):
        attrs = msg.media.document.attributes
        if any(isinstance(a, DocumentAttributeAudio) and a.voice for a in attrs):
            return "voice"
        if any(isinstance(a, DocumentAttributeVideo) for a in attrs):
            return "video"
        return "document"
    return None


async def download_and_get_content(msg_type: str, msg, client: TelegramClient) -> dict:
    if msg_type == "text":
        return {"content": msg.message}

    if msg_type == "photo":
        dest = settings.get_media_path("images")
        dest.mkdir(parents=True, exist_ok=True)
        path = await client.download_media(msg.media, file=str(dest) + "/")
        return {"file_path": path}

    doc = msg.media.document
    result = {"file_mime_type": doc.mime_type}

    # Имя файла для документов
    for attr in doc.attributes:
        if hasattr(attr, "file_name"):
            result["file_name"] = attr.file_name
            break

    # Определяем папку по типу
    folder = "voice" if msg_type == "voice" else "docs"
    dest = settings.get_media_path(folder)
    dest.mkdir(parents=True, exist_ok=True)
    path = await client.download_media(msg.media, file=str(dest) + "/")
    result["file_path"] = path

    return result


async def handle_forwarded(msg, client: TelegramClient) -> dict:
    result = {"forwarded_create_data": msg.fwd_from.date.replace(tzinfo=None)}
    origin = msg.fwd_from

    if origin.from_id and hasattr(origin.from_id, "user_id"):
        user_id = origin.from_id.user_id
        if user_id == msg.sender_id:
            info = "Автор переслал своё собственное сообщение"
        elif user_id in settings.FAMILY_CHAT_IDS:
            info = f"Автор переслал сообщение от {settings.FAMILY_CHAT_IDS[user_id]}"
        else:
            info = f"Автор переслал сообщение от пользователя id={user_id}"
        result["forwarded_msg_info"] = info

    if origin.from_id and hasattr(origin.from_id, "channel_id"):
        try:
            entity = await client.get_entity(origin.from_id)
            title = entity.title
        except Exception:
            title = "неизвестный канал"
        result["forwarded_msg_info"] = f"Переслано из канала '{title}'"

    return result


async def get_last_tlg_msg_id() -> int:
    # Берём максимальный tlg_msg_id из локальной БД как offset
    async with get_db() as session:
        result = await session.execute(
            select(func.max(LocalRawMessages.tlg_msg_id))
        )
        last_id = result.scalar_one_or_none()
        return last_id if last_id else 0


async def get_last_session_id(session) -> int:
    result = await session.execute(
        select(func.max(LocalRawMessages.session_id))
    )
    val = result.scalar_one_or_none()
    return val if val else 0


async def get_thread_last_msg(session, message_thread: str):
    # Последнее сообщение конкретного треда — для логики сессий
    result = await session.execute(
        select(LocalRawMessages)
        .where(LocalRawMessages.message_thread == message_thread)
        .order_by(LocalRawMessages.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def resolve_session_id(session, message_thread: str, msg_time: datetime) -> int:
    last_msg = await get_thread_last_msg(session, message_thread)

    if last_msg is None:
        # Первое сообщение в этом треде — новая сессия
        return await get_last_session_id(session) + 1

    threshold = settings.MSG_SESSION_THRESHOLD.get(message_thread)

    if threshold is None:
        # Треды без порога (calendar, task) — каждое сообщение своя сессия
        return await get_last_session_id(session) + 1

    last_time = datetime.fromisoformat(str(last_msg.created_at))
    delta = timedelta(minutes=threshold)
    is_new_session = (last_time + delta) < msg_time

    if is_new_session:
        return await get_last_session_id(session) + 1
    else:
        return last_msg.session_id


async def collect_and_save():
    await ensure_db_initialized()
    last_id = await get_last_tlg_msg_id()

    async with TelegramClient(
        "family_atlas",
        settings.TG_API_ID,
        settings.TG_API_HASH,
    ) as client:
        new_messages = []

        # Собираем сообщения из каждого треда отдельно
        for thread_id, thread_name in THREAD_MAPS.items():
            async for msg in client.iter_messages(
                PeerChannel(channel_id=settings.FORUM_CHAT_ID),
                reply_to=thread_id,
                # min_id фильтрует сообщения старше последнего сохранённого
                min_id=last_id,
                limit=5,
            ):
                new_messages.append((thread_name, msg))

        if not new_messages:
            logger.info("Новых сообщений нет")
            return 0

        # Сортируем по id чтобы сессии назначались в правильном порядке
        new_messages.sort(key=lambda x: x[1].id)
        logger.info(f"Получено {len(new_messages)} новых сообщений")

        async with get_db() as session:
            for thread_name, msg in new_messages:
                msg_type = detect_msg_type(msg)
                if not msg_type:
                    logger.debug(f"Неизвестный тип сообщения: {msg.id}")
                    continue

                author_id = msg.sender_id
                author_name = settings.FAMILY_CHAT_IDS.get(author_id)
                if not author_name:
                    logger.error(f"Неизвестный автор: {author_id}")
                    continue

                msg_time = msg.date.replace(tzinfo=None)
                session_id = await resolve_session_id(session, thread_name, msg_time)

                params = {
                    "msg_type": msg_type,
                    "author_name": author_name,
                    "author_username": getattr(msg.sender, "username", "") or "",
                    "message_thread": thread_name,
                    "created_at": str(msg_time),
                    "session_id": session_id,
                    "session_status": "ready",
                }
                params.update(await download_and_get_content(msg_type, msg, client))

                if msg.fwd_from:
                    params.update(await handle_forwarded(msg, client))

                if msg.message and msg_type != "text":
                    # caption — текст при медиа сообщении
                    params["caption"] = msg.message

                raw_msg, created = await get_or_create(
                    session=session,
                    model=LocalRawMessages,
                    search_params={"tlg_msg_id": msg.id},
                    create_params=params,
                )
                if created:
                    session.add(raw_msg)
                    logger.debug(f"Сохранено: {raw_msg}")

            await session.commit()

    return len(new_messages)