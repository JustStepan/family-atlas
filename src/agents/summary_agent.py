from datetime import datetime, date

from langgraph.graph import StateGraph

from src.agents.summary_graph import SummaryState
from src.agents.writer import write_summary_note
from src.database.engine import get_db
from src.database.models import WeeklySummary
from src.database.utils import last_iso_week_range, get_last_summary
from src.infrastructure.context import AppContext
from src.infrastructure.embeddings import get_embedding_model
from src.msg_collector.telethon_sender import send_summary
from src.config import settings
from src.logger import logger
from sqlalchemy import select


async def _already_done(session, period_end: str) -> bool:
    """Идемпотентность: не суммируем одну неделю дважды."""
    q = await session.execute(
        select(WeeklySummary.id).where(WeeklySummary.period_end == period_end)
    )
    return q.scalar_one_or_none() is not None


async def run_weekly_summary(graph: StateGraph, today: date | None = None):
    today = today or date.today()
    start, end = last_iso_week_range(today)
    period_start, period_end = str(start), str(end)

    async with get_db() as session:
        if await _already_done(session, period_end):
            logger.info(f"Сводка за неделю {period_end} уже есть, пропускаем")
            return

    # генерация — под одной загруженной моделью
    async with AppContext() as ctx:
        await ctx.use_model(settings.SUMMARY_AGENT_MODEL)
        async with get_db() as session:
            result = await graph.ainvoke(
                SummaryState(period_start=period_start, period_end=period_end),
                config={"configurable": {"llm": ctx.llm, "session": session}},
            )

    if not result.get("content"):
        return  # пустая неделя — гейт уже залогировал

    content = result["content"]
    # 1. файл в Obsidian
    write_summary_note(period_start, period_end, content)
    # 2. отправка
    sent = await send_summary(content)
    # 3. запись в БД
    async with get_db() as session:
        session.add(WeeklySummary(
            period_start=period_start,
            period_end=period_end,
            content=content,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sent_to_telegram=sent,
        ))
        await session.commit()
    logger.info(f"Сводка за {period_start}–{period_end} сохранена")