from datetime import datetime, timedelta, date
from itertools import chain
from collections import Counter

from sqlalchemy import select

from src.database.models import AssembledMessages, Person, WeeklySummary 


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
            # calendar
            "event_time": m.event_time,
            "event_end_time": m.event_end_time,
            "location": m.location,
            "is_recurring": m.is_recurring,
            "google_calendar_link": m.google_calendar_link,
            # task
            "deadline": m.deadline,
            "is_done": m.is_done or False,
            "priority": m.priority,
        }
        for m in rows
    ]


def first_n_objects(lst: list[str], amount: int) -> list[str]:
    count_obj = Counter(lst).most_common(amount)
    return [obj[0] for obj in count_obj]


async def get_existing_tags(session) -> list[str]:
    all_tags_q = await session.execute(select(AssembledMessages.tags))
    all_tags = list(chain.from_iterable(
        t for t in all_tags_q.scalars().all() if t
    ))
    top_all = first_n_objects(all_tags, 40)
    
    # свежие теги (последние 30 дней)
    recent_q = await session.execute(
        select(AssembledMessages.tags)
        .where(AssembledMessages.created_at >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"))
    )
    recent_tags = list(chain.from_iterable(
        t for t in recent_q.scalars().all() if t
    ))
    top_recent = first_n_objects(recent_tags, 40)
    
    return list(dict.fromkeys(top_all + top_recent))  # дедупликация


async def get_existing_persons(session) -> dict[str, list]:
    persons_query = await session.execute(
        select(Person.name, Person.contexts)
        .where(Person.contexts.isnot(None))
        .order_by(Person.last_seen.desc())
        .limit(50)
    )
    rows = persons_query.all()
    return {name: contexts for name, contexts in rows}


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


def last_iso_week_range(today: date) -> tuple[date, date]:
    """Границы ПРОШЛОЙ календарной недели (пн-вс) относительно сегодня."""
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return last_monday, last_sunday


async def get_week_done_msgs(session, start: date, end: date) -> dict[str, list[dict]]:
    """Done-заметки за неделю, сгруппированные по треду. Отбор по реальной дате (created_at)."""
    # created_at — строка "YYYY-MM-DD HH:MM:SS", сравнение строк работает лексикографически
    start_s = f"{start} 00:00:00"
    end_s = f"{end} 23:59:59"
    q = await session.execute(
        select(AssembledMessages)
        .where(AssembledMessages.status == "done")
        .where(AssembledMessages.created_at >= start_s)
        .where(AssembledMessages.created_at <= end_s)
        .order_by(AssembledMessages.created_at)
    )
    rows = q.scalars().all()

    grouped: dict[str, list[dict]] = {"diary": [], "notes": [], "calendar": [], "task": []}
    for m in rows:
        grouped.setdefault(m.message_thread, []).append({
            "title": m.title,
            "summary": m.summary,
            "created_at": m.created_at,
            # для задач нужен статус выполнения
            "is_done": m.is_done,
            "event_time": m.event_time,
        })
    return grouped


async def get_last_summary(session) -> str | None:
    """Текст последней сводки — для преемственности в новой."""
    q = await session.execute(
        select(WeeklySummary.content)
        .order_by(WeeklySummary.period_end.desc())
        .limit(1)
    )
    return q.scalar_one_or_none()