from datetime import datetime, date

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, NotRequired

from src.agents.schemas import WeeklySummaryOutput
from src.database.utils import get_week_done_msgs, get_last_summary, last_iso_week_range
from src.prompts.summary_prompt import SUMMARY_PROMPT
from src.logger import logger


class SummaryState(TypedDict):
    period_start: str
    period_end: str
    facts: NotRequired[str]          # детерминированно собранный текст фактов
    prev_summary: NotRequired[str | None]
    content: NotRequired[str]        # итоговый текст от LLM
    has_data: NotRequired[bool]      # были ли done-заметки


def _format_facts(grouped: dict[str, list[dict]]) -> str:
    """Без LLM собираем факты по тредам в плоский текст для промпта."""
    blocks = []
    labels = {"diary": "Дневник", "notes": "Заметки", "calendar": "События"}
    for thread, label in labels.items():
        items = grouped.get(thread) or []
        if items:
            lines = "\n".join(f"- {it['title']}: {it['summary']}" for it in items)
            blocks.append(f"{label}:\n{lines}")

    tasks = grouped.get("task") or []
    if tasks:
        done = [t for t in tasks if t.get("is_done")]
        undone = [t for t in tasks if not t.get("is_done")]
        t_lines = []
        if done:
            t_lines.append("Выполнено: " + ", ".join(t["title"] for t in done))
        if undone:
            t_lines.append("Осталось: " + ", ".join(t["title"] for t in undone))
        blocks.append("Задачи:\n" + "\n".join(t_lines))

    return "\n\n".join(blocks)


async def collect_facts(state: SummaryState, config: RunnableConfig) -> dict:
    session = config["configurable"]["session"]
    start = date.fromisoformat(state["period_start"])
    end = date.fromisoformat(state["period_end"])

    grouped = await get_week_done_msgs(session, start, end)
    facts = _format_facts(grouped)
    if not facts:
        logger.info(f"Сводка: нет done-заметок за {start}–{end}, пропускаем")
        return {"has_data": False}

    prev = await get_last_summary(session)
    logger.info(f"Сводка: факты собраны за {start}–{end}, прошлая сводка: {'есть' if prev else 'нет'}")
    return {"facts": facts, "prev_summary": prev, "has_data": True}


async def generate_summary(state: SummaryState, config: RunnableConfig) -> dict:
    if not state.get("has_data"):
        return {}

    llm = config["configurable"]["llm"]
    prev_block = f"\n\nСводка за прошлую неделю:\n{state['prev_summary']}" if state.get("prev_summary") else ""
    hum_msg = HumanMessage(content=(
        f"Период: {state['period_start']} — {state['period_end']}\n\n"
        f"Факты за неделю:\n{state['facts']}{prev_block}"
    ))
    structured_llm = llm.with_structured_output(WeeklySummaryOutput)
    result = await structured_llm.ainvoke([SystemMessage(content=SUMMARY_PROMPT), hum_msg])
    logger.info("Сводка: текст сгенерирован")
    return {"content": result.content}


def summary_graph_builder():
    graph = StateGraph(SummaryState)
    graph.add_node("collect", collect_facts)
    graph.add_node("generate", generate_summary)
    graph.add_edge(START, "collect")
    graph.add_edge("collect", "generate")
    graph.add_edge("generate", END)
    return graph.compile(checkpointer=None)