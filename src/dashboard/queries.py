from collections import Counter
from itertools import chain

from sqlalchemy import select, func

from src.database.models import AssembledMessages, Person, WeeklySummary


async def get_stats(session) -> dict:
    by_thread = dict((await session.execute(
        select(AssembledMessages.message_thread, func.count())
        .group_by(AssembledMessages.message_thread))).all())
    by_status = dict((await session.execute(
        select(AssembledMessages.status, func.count())
        .group_by(AssembledMessages.status))).all())

    related_lists = [r for r in (await session.execute(
        select(AssembledMessages.related))).scalars().all() if r]
    total_related = sum(len(r) for r in related_lists)
    avg_related = round(total_related / len(related_lists), 2) if related_lists else 0

    persons = (await session.execute(select(func.count()).select_from(Person))).scalar()
    summaries = (await session.execute(select(func.count()).select_from(WeeklySummary))).scalar()

    all_tags = list(chain.from_iterable(
        t for t in (await session.execute(select(AssembledMessages.tags))).scalars().all() if t))
    counts = Counter(all_tags)

    return {
        "total_notes": sum(by_thread.values()),
        "by_thread": by_thread,
        "by_status": by_status,
        "total_related": total_related,
        "avg_related": avg_related,
        "persons_count": persons,
        "summaries_count": summaries,
        "unique_tags": len(counts),
        "top_tags": counts.most_common(15),
        "drift_candidates": sorted(t for t, c in counts.items() if c == 1),  # встретились 1 раз
    }


async def get_diagnostics(session, limit: int = 30) -> list[dict]:
    rows = (await session.execute(
        select(AssembledMessages)
        .where(AssembledMessages.status.in_(["analyzed", "done"]))
        .order_by(AssembledMessages.id.desc())
        .limit(limit))).scalars().all()
    return [{
        "id": m.id, "thread": m.message_thread, "raw_content": m.raw_content,
        "title": m.title, "summary": m.summary,
        "tags": m.tags or [], "people": m.people_mentioned or [],
    } for m in rows]


async def get_person_names(session) -> list[str]:
    return list((await session.execute(
        select(Person.name).order_by(Person.name))).scalars().all())