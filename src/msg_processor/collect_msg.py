import httpx
from sqlalchemy import select

from src.config import settings
from src.logger import logger
from src.database.engine import ensure_db_initialized, get_db
from src.database.models import LocalRawMessages


async def fetch_ready_messages() -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{settings.COLLECTOR_URL}/messages/ready/",
            headers={"x-api-key": settings.COLLECTOR_API_KEY}
        )
        r.raise_for_status()
        return r.json()


async def get_or_create(session, model, search_params, create_params=None):
    query = select(model).filter_by(**search_params)
    obj = (await session.execute(query)).scalar_one_or_none()
    if obj:
        return obj, False
    all_params = {**(create_params or {}), **search_params}
    obj = model(**all_params)
    return obj, True


async def save_msgs() -> int:
    messages = await fetch_ready_messages()
    if not messages:
        logger.info('Собрано 0 сообщений')
        return 0

    await ensure_db_initialized()
    async with get_db() as session:
        for msg in messages:
            try:
                original_id = msg['id']
                create_params = {k: v for k, v in msg.items() if k not in ('id', 'author')}
                create_params['author_name'] = msg['author']['author_name']
                create_params['author_username'] = msg['author']['author_username']
                message, create = await get_or_create(
                    session=session,
                    model=LocalRawMessages,
                    search_params={"original_id": original_id},
                    create_params=create_params
                )
                if create:
                    session.add(message)
            except Exception as e:
                logger.error(f'Ошибка сохранения сообщения {original_id}: {e}')
        await session.commit()
    return len(messages)


async def mark_messages_done(ids: list[int]):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.COLLECTOR_URL}/messages/done/",
            headers={"x-api-key": settings.COLLECTOR_API_KEY},
            json={"ids": ids}
        )
        r.raise_for_status()
        return r.json()