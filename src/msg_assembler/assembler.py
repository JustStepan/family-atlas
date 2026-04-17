from sqlalchemy import select, update

from src.msg_assembler.voice_recognition import process_voice_messages
from src.msg_assembler.docs_saver import MIME_TO_HANDLER, process_doc_messages
from src.database.models import AssembledMessages, LocalRawMessages
from src.msg_assembler.image_describer import process_photo_messages
from src.infrastructure.context import get_llm_model
from src.database.engine import get_db
from src.logger import logger


MSG_TYPE_MAP = {
    "voice": "Голосовое сообщение",
    "text": "Текстовое сообщение",
    "photo": "Сообщение, содержащее фото",
    "video": "Сообщение, содержащее видео",
    "document": "Сообщение, содержащее документ",
}


async def prepare_msgs():
    async with get_db() as session:
        query = await session.execute(
            select(LocalRawMessages)
            .where(LocalRawMessages.session_status == "ready")
            .order_by(LocalRawMessages.session_id, LocalRawMessages.id)
        )
        messages = query.scalars().all()

        if not messages:
            logger.info('Нет сообщений для обработки')
            return []

        photo_msgs = [m for m in messages if m.msg_type == "photo"]
        docs_msgs = [m for m in messages if m.msg_type in ["document", "video"]]
        voice_msgs = [m for m in messages if m.msg_type == "voice"]
        txt_msgs = [m for m in messages if m.msg_type == "text"]

        # нужен ли vision для документов
        vision_in_docs = any(m.file_mime_type in MIME_TO_HANDLER for m in docs_msgs)

        if voice_msgs:
            logger.info(f'Обрабатываем аудио сообщения: {len(voice_msgs)} шт.')
            voice_msgs = await process_voice_messages(voice_msgs)

        if photo_msgs or vision_in_docs:
            async with get_llm_model() as ctx:
                await ctx.use_model("vision")
                if photo_msgs:
                    logger.info(f'Обрабатываем фото: {len(photo_msgs)} шт.')
                    photo_msgs = await process_photo_messages(ctx, photo_msgs)
                if docs_msgs:
                    logger.info(f'Обрабатываем документы c vision: {len(docs_msgs)} шт.')
                    docs_msgs = await process_doc_messages(docs_msgs, ctx)

        elif docs_msgs: 
            logger.info(f'Обрабатываем документы (pdf, zip, etc): {len(docs_msgs)} шт.')
            docs_msgs = await process_doc_messages(docs_msgs)

        if txt_msgs:
            logger.info(f'Обрабатываем текстовые сообщения: {len(txt_msgs)} шт.')
            for msg in txt_msgs:
                msg.msg_status = 'done'

        msgs_for_assembling = voice_msgs + photo_msgs + docs_msgs + txt_msgs
        msgs_for_assembling.sort(key=lambda m: (m.session_id, m.id))

        try:
            done_ids = await assembler(session, msgs_for_assembling)
        except Exception as e:
            logger.error(f'Ошибка в assembler: {e}')
            raise

        await update_local_msg_status(session, done_ids)
        await session.commit()
        
        return done_ids


async def update_local_msg_status(session, tlg_msg_id):
    try:
        await session.execute(
            update(LocalRawMessages)
            .where(LocalRawMessages.tlg_msg_id.in_(tlg_msg_id))
            .values(session_status="done")
        )
    except Exception as e:
        logger.error(f'Произошла ошибка изменения статуса локальной бд: {e}')

    return {"message": "Статус сообщений локальной БД успешно изменен"}


async def assembler(session, messages) -> list[int]:
    if not messages:
        return []

    last_session_id = None
    session_data = []
    new_data = {}

    for msg in messages:
        content = (
            f'[{MSG_TYPE_MAP[msg.msg_type]} от автора: {msg.author_name}]\n'
            f'- Содержание: {msg.content}\n'
            f'- Дата создания: {msg.created_at}'
        )

        if msg.forwarded_msg_info:
            content += (
                f'\n- {msg.forwarded_msg_info}. '
                f'Оригинальное сообщение создано: {msg.forwarded_create_data}'
            )

        if msg.file_name:
            content += f'\n- Имя прикреплённого файла: {msg.file_name}'

        if msg.caption:
            content += f'\n- Заголовок прикреплённого документа: {msg.caption}'

        if msg.session_id == last_session_id:
            new_data["content"] += f'\n\nЕщё одно сообщение этой темы:\n{content}'
        else:
            if last_session_id is not None:
                session_data.append(new_data)
            new_data = {
                "message_thread": msg.message_thread,
                "content": content,
                "session_id": msg.session_id,
            }
            last_session_id = msg.session_id

    # добавляем последнюю сессию
    if new_data:
        session_data.append(new_data)

    for ss in session_data:
        # проверяем что такая сессия ещё не собрана
        existing = await session.execute(
            select(AssembledMessages).filter_by(session_id=ss["session_id"])
        )
        if existing.scalar_one_or_none():
            logger.debug(f'Сессия {ss["session_id"]} уже собрана, пропускаем')
            continue

        assembled = AssembledMessages(
            raw_content=ss["content"],
            session_id=ss["session_id"],
            message_thread=ss["message_thread"],
        )
        session.add(assembled)
        logger.debug(f'Добавлена сессия {ss["session_id"]}')

    return [m.tlg_msg_id for m in messages]