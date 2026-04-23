from itertools import chain

from sqlalchemy import select

from src.database.models import AssembledMessages, Person


async def get_or_create(session, model, search_params, create_params=None):
    query = select(model).filter_by(**search_params)
    obj = (await session.execute(query)).scalar_one_or_none()
    if obj:
        return obj, False
    all_params = {**(create_params or {}), **search_params}
    obj = model(**all_params)
    return obj, True


async def get_assembled_msgs(session):
    query = await session.execute(
        select(AssembledMessages)
        .where(AssembledMessages.status == "ready")
    )
    ready_sessions = query.scalars().all()
    if ready_sessions: 
        print(f'получено {len(ready_sessions)} сообщений')
    return ready_sessions


async def get_existing_tags(session) -> list[str]:
    query = await session.execute(
        select(AssembledMessages.tags))
    result = [tags for tags in query.scalars().all() if tags is not None]
    return list(set(chain.from_iterable(result)))


async def get_known_persons(session) -> list[str]:
    query = await session.execute(select(Person.name))
    return list(set(query.scalars().all()))
