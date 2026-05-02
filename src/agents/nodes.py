from pathlib import Path

import pymorphy3
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy import update

from src.database.models import AssembledMessages
from src.database.utils import get_existing_tags_and_persons, get_summaries
from src.agents.schemas import FamilyAtlasState, choose_state
from src.logger import logger
from src.config import settings
from src.helpers.find_relatives import find_candidates


morph = pymorphy3.MorphAnalyzer()


async def assembld_text_analyzer(
    state: FamilyAtlasState, config: RunnableConfig
) -> dict:
    logger.info(
        f"Начинаем обработку сессии: {state['session_id']} - {state['message_thread']}"
    )
    tread_type = state["message_thread"]
    system_prompt, pdtc_output = choose_state(tread_type)

    llm = config["configurable"]["llm"]
    session = config["configurable"]["session"]

    existing_tags, known_persons = await get_existing_tags_and_persons(session)
    logger.info(
        f"Передаем на обработку существующие теги ({len(existing_tags)} шт.) и персоналии ({len(known_persons)} шт.)"
    )

    context = f"\nСуществующие теги: {', '.join(existing_tags)}"
    context += f"\nИзвестные персоны: {', '.join(known_persons)}"
    hum_msg = HumanMessage(
        content=(
            f"Автор сообщения: {state['author_name']} — не включай его в people_mentioned\n"
            f"Обработай текст:\n{state['raw_content']}\n"
            f"Время: {state['created_at']}\n{context}"
        )
    )
    system_msg = SystemMessage(content=system_prompt)
    structured_llm = llm.with_structured_output(pdtc_output)

    for attempt in range(1, settings.AGENT_ATTEMPTS + 1):
        try:
            result = await structured_llm.ainvoke([system_msg, hum_msg])
            logger.info(f"Результат анализа: {result.model_dump()}")
            return result.model_dump()
        except Exception as e:
            logger.warning(f"Попытка {attempt} неудачна: {e}")
            if attempt == settings.AGENT_ATTEMPTS:
                logger.error("Все попытки исчерпаны")
                return {"status": "error"}


async def db_updater(state: FamilyAtlasState, config: RunnableConfig) -> dict:
    session = config["configurable"]["session"]
    embedding_model = config["configurable"]["embedding_model"]
    embedding = embedding_model.encode(state.get("summary")).tolist()

    thread = state["message_thread"]
    if thread == "task":
        obsidian_path = str(settings.get_note_path(thread, state["created_at"]))
    else:
        obsidian_path = str(
            settings.get_note_path(thread, state["created_at"], state.get("title"))
        )

    try:
        await session.execute(
            update(AssembledMessages)
            .where(AssembledMessages.session_id == state["session_id"])
            .values(
                title=state.get("title"),
                summary=state.get("summary"),
                tags=state.get("tags"),
                content=state.get("content"),
                people_mentioned=state.get("people_mentioned"),
                obsidian_path=obsidian_path,
                embedding=embedding,
                related=state.get("related"),
                status="analyzed",
                # calendar
                event_time=state.get("event_time"),
                event_end_time=state.get("event_end_time"),
                location=state.get("location"),
                is_recurring=state.get("is_recurring"),
                # task
                deadline=state.get("deadline"),
                is_done=state.get("is_done"),
                priority=state.get("priority"),
            )
        )
        await session.commit()
        logger.info(f"Assembled сообщение {state['session_id']} сохранено в БД")
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")
        await session.execute(
            update(AssembledMessages)
            .where(AssembledMessages.session_id == state["session_id"])
            .values(status="error")
        )
        await session.commit()
    return {}


def _get_candidate_summaries(
    candidates_idxs: set[int], session_ids: list[int], summaries: list[str]
) -> list[dict]:
    return [
        {"session_id": session_ids[idx], "session_summary": summaries[idx]}
        for idx in candidates_idxs
    ]


async def find_relatives(
    state: FamilyAtlasState, config: RunnableConfig
) -> dict:
    if not state.get("summary"):
        return {"related": []}

    session = config["configurable"]["session"]
    summ_data = await get_summaries(session)
    if not summ_data.get("summaries"):
        return {"related": []}

    embedding_model = config["configurable"]["embedding_model"]
    candidates_idxs = find_candidates(
        state["summary"],
        summ_data.get("summaries"),
        summ_data.get("embeddings"),
        morph,
        embedding_model,
    )
    if not candidates_idxs:
        return {"related": []}

    llm = config["configurable"]["llm"]
    system_prompt, pdtc_output = choose_state("find_relatives")
    candidates = _get_candidate_summaries(
        candidates_idxs,
        summ_data.get("session_ids"),
        summ_data.get("summaries"),
    )
    hum_msg = HumanMessage(
        content=(
            f"Summary исходного сообщения:\n{state['summary']}\n\n"
            f"Список кандидатов для сравнения:\n{candidates}"
        )
    )
    structured_llm = llm.with_structured_output(pdtc_output)
    result_ids = await structured_llm.ainvoke([SystemMessage(content=system_prompt), hum_msg])
    if not result_ids.session_ids:
        return {"related": []}

    s_id_to_path = dict(zip(summ_data["session_ids"], summ_data["obsidian_path"]))
    related = [
        Path(s_id_to_path[sid]).stem
        for sid in result_ids.session_ids
        if sid in s_id_to_path
    ]
    logger.info(
        f"find_relatives: найдено {len(related)} связанных заметок для session_id={state['session_id']}"
    )
    return {"related": related}