from datetime import datetime
import pprint

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from sqlalchemy.ext.asyncio import AsyncSession
from src.database.engine import ensure_db_initialized, get_db
from src.database.models import RawMessages, Author
from src.logger import logger
from src.config import settings
from src.telegram.collector import collect_messages


CONTEXT_MAP = {
    "text": "text",
    "document": "doc_id",
    "photo": "photo_id",
    "voice": "voice_id",
}


async def get_or_create(session: AsyncSession, model, params):
    query = select(model).filter_by(**params)
    obj = (await session.execute(query)).scalar_one_or_none()
    
    if obj:
        return obj
    
    obj = model(**params)
    session.add(obj)
    await session.commit()
    return obj


async def get_last_value(session):
    query = (
        select(RawMessages.session_id)
        .order_by(desc(RawMessages.session_id))
        .limit(1)
    )
    result = await session.execute(query)
    last_value = result.scalar()
    return last_value if last_value is not None else 0


async def get_content(msg: dict) -> str:
    msg_type = msg['msg_type']
    return msg[CONTEXT_MAP[msg_type]]


async def create_raw_msgs():

    # Проверяем существует ли БД
    await ensure_db_initialized()
    # собираем последние сообщения из телеграм
    messages = await collect_messages()

    async with get_db() as session:
        for msg in messages:
            params = {
                "tlg_author_id": msg["author_id"],
                "author_name": settings.FAMILY_CHAT_IDS[msg["author_id"]],
                "author_username": msg["author_username"],
            }
            author = await get_or_create(session, Author, params)

            # работаем теперь с RawMessages таблицей
            last_session_id = await get_last_value(session)

            content = await get_content(msg)

            rw_msg_params = {
                "session_id": last_session_id + 1,
                "message_thread": msg["message_thread"],
                "msg_type": msg["msg_type"],
                "content": content,
                "author": author,
            }

            rw_msg = await get_or_create(session, RawMessages, rw_msg_params)
            await session.refresh(rw_msg)
            print(rw_msg)

            # pprint.pprint(msg)
            # print()
