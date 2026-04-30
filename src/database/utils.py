from itertools import chain
from collections import Counter

from sqlalchemy import select

from src.database.engine import get_db
from src.database.models import AssembledMessages


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
        print(f'Получено {len(ready_sessions)} ready-сообщений')
    return ready_sessions


async def get_analyzed_msgs(session) -> list[dict]:
    query = await session.execute(
        select(AssembledMessages)
        .where(AssembledMessages.status == "analyzed")
    )
    rows = query.scalars().all()
    if rows:
        print(f'Получено {len(rows)} analyzed-сообщений')
    return [
        {
            "session_id": m.session_id,
            "message_thread": m.message_thread,
            "created_at": m.created_at,
            "author_name": m.author_name,
            "title": m.title,
            "summary": m.summary,
            "content": m.content,
            "tags": m.tags or [],
            "people_mentioned": m.people_mentioned or [],
            "related": m.related or [],
            "attachments": m.attachments or [],
            "obsidian_path": m.obsidian_path,
            "deadline": None,
            "is_done": False,
            "priority": None,
            "event_time": None,
            "location": None,
        }
        for m in rows
    ]


def first_n_objects(lst: list[str], amount: int) -> list[str]:
    count_obj = Counter(lst).most_common(amount)
    return [obj[0] for obj in count_obj]


async def get_existing_tags_and_persons(session) -> tuple[list[str], list[str]]:
    tags_query = await session.execute(
        select(AssembledMessages.tags))
    persons_query = await session.execute(
        select(AssembledMessages.people_mentioned))
    
    tags = [t for t in tags_query.scalars().all() if t is not None]
    persons = [p for p in persons_query.scalars().all() if p is not None]
    
    return (
        first_n_objects(chain.from_iterable(tags), 30),
        first_n_objects(chain.from_iterable(persons), 30)
    )


async def get_summaries(session) -> dict[str, list]:
    result = await session.execute(
        select(
            AssembledMessages.session_id,
            AssembledMessages.summary,
            AssembledMessages.obsidian_path,
            AssembledMessages.embedding,
        )
        .where(AssembledMessages.summary.isnot(None))
        .where(AssembledMessages.obsidian_path.isnot(None))
        .where(AssembledMessages.embedding.isnot(None))
    )
    rows = result.all()
    if not rows:
        return {}

    return {
        "session_ids": [row[0] for row in rows],
        "summaries": [row[1] for row in rows],
        "obsidian_path": [row[2] for row in rows],
        "embeddings": [row[3] for row in rows]
    }
