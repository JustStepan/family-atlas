from pathlib import Path

import frontmatter as fm
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
        f"Начинаем обработку сессии: {state["session_id"]} - {state["message_thread"]}"
    )

    tread_type = state["message_thread"]
    system_prompt, pdtc_output = choose_state(tread_type)
    thread_content = state["raw_content"]

    llm = config["configurable"]["llm"]
    session = config["configurable"]["session"]

    existing_tags, known_persons = await get_existing_tags_and_persons(session)
    logger.info(
        f"Передаем на обработку существующие теги ({len(existing_tags)} шт.) и персоналии ({len(known_persons)} шт.)"
    )

    created_at = state["created_at"]

    context = f"\nСуществующие теги: {', '.join(existing_tags)}"
    context += f"\nИзвестные персоны: {', '.join(known_persons)}"
    hum_msg = HumanMessage(
        content=(
            f"Автор сообщения: {state['author_name']} — не включай его в people_mentioned\n"
            f"Обработай текст:\n{thread_content}\n"
            f"Время: {created_at}\n{context}"
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
                logger.error(f"Все попытки исчерпаны")
                return {"status": "error"}


def thread_router(state: FamilyAtlasState) -> str:
    logger.info(
        f"Функция 'thread_router'. Session: {state["session_id"]} - {state["message_thread"]}"
    )
    return state["message_thread"]


def get_frontmatter(state: FamilyAtlasState) -> str:
    tags_yaml = "\n".join(f"  - {tag}" for tag in state["tags"])
    people = state.get("people_mentioned") or []
    people_yaml = "\n".join(f"  - {person_to_wikilink(p)}" for p in people)
    related = state.get("related") or []
    related_yaml = "\n".join(f'  - "[[{Path(r).stem}]]"' for r in related)

    logger.info(
        f"Frontmatter: {len(state['tags'])} тегов, {len(people)} персон, {len(related)} related"
    )
    return (
        "---\n"
        f"author: {state['author_name']}\n"
        f"created: {state['created_at']}\n"
        f"thread: {state['message_thread']}\n"
        f"tags:\n{tags_yaml}\n"
        f"people_mentioned:\n{people_yaml}\n"
        f"related: \n{related_yaml}\n"
        "---"
    )


def create_file(obsidian_path: Path, content: str) -> dict:
    try:
        if obsidian_path.exists():
            logger.warning(f"Файл уже существует: {obsidian_path}")
            return {"obsidian_path": str(obsidian_path), "status": "exists"}

        obsidian_path.write_text(content, encoding="utf-8")
        logger.info(f"Файл {obsidian_path.name} успешно записан в хранилище")
        return {"obsidian_path": str(obsidian_path), "status": "written"}
    except Exception as e:
        logger.error(f"Во время записи файла произошла ошибка: {e}")
        return {"obsidian_path": str(obsidian_path), "status": "error"}


async def diary_note_calend_file_writer(state: FamilyAtlasState) -> dict:
    # write this fields into obsidian vault
    obsidian_path = settings.get_note_path(
        state["message_thread"], state["created_at"], state["title"]
    )
    # Проверяем существует ли файл/папка obsidian
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)

    # Формируем содержание файла
    frontmatter = get_frontmatter(state)
    body = f"# {state['title']}\n\n{state['content']}"
    attachments = state.get("attachments") or []

    if calend_additions := add_addition_calend_fields(state):
        body += calend_additions
    if attachments:
        links = "\n".join(f"![[{Path(p).name}]]" for p in attachments)
        body += f"\n\n## Вложения\n{links}"

    full_content = frontmatter + "\n\n" + body

    # Пробуем записать контент в файл
    return create_file(obsidian_path, full_content)


def add_addition_calend_fields(state: FamilyAtlasState) -> str:
    add_str = ""
    if state.get("event_time"):
        add_str += f"\n---\nВремя события: {state.get('event_time')}"
    if state.get("location"):
        add_str += f", Место события: {state.get('location')}"
    return add_str


def person_to_wikilink(name: str) -> str:
    if name.startswith("[["):
        return f'"{name}"'
    return f"[[persons/{name}]]"


def add_frontmatter_fields(
    obsidian_path: Path, tags: list[str], people: list[str], body
):
    post = fm.load(obsidian_path)
    post["tags"] = list(set((post.get("tags") or []) + tags))
    post["people_mentioned"] = list(
        set(
            (post.get("people_mentioned") or [])
            + [person_to_wikilink(p) for p in people]
        )
    )
    post.content += "\n\n" + body

    try:
        with open(obsidian_path, "w", encoding="utf-8") as f:
            f.write(fm.dumps(post))
            logger.info(
                f"Задача добавлена в существующий файл: {obsidian_path.name}"
            )
            return {"obsidian_path": str(obsidian_path), "status": "rewritten"}
    except Exception as e:
        logger.error(
            f"Во время добавления контента к файлу произошла ошибка: {e}"
        )
        return {"obsidian_path": str(obsidian_path), "status": "error"}


def add_to_file(obsidian_path, content) -> dict:
    try:
        with open(obsidian_path, "a", encoding="utf-8") as f:
            f.write(content)
            return {"obsidian_path": str(obsidian_path), "status": "written"}
    except Exception as e:
        logger.error(
            f"Во время добавления контента к файлу произошла ошибка: {e}"
        )
        return {"obsidian_path": str(obsidian_path), "status": "error"}


def add_task_fields(state: FamilyAtlasState) -> str:
    body = ""
    checkbox = "- [x]" if state.get("is_done") else "- [ ]"
    body += f'\n{checkbox} **{state["title"]}**'
    if state.get("deadline"):
        body += f'\n📅 Дедлайн: {state["deadline"]}'
    if state.get("priority"):
        body += f'\n⚡ Приоритет: {state["priority"]}'
    body += f"\n{state['content']}"
    if attachments := state.get("attachments") or []:
        links = "\n".join(f"![[{Path(p).name}]]" for p in attachments)
        body += f"\n\n### Вложения\n{links}"
    return body + "\n\n---"


async def task_file_writer(state: FamilyAtlasState) -> dict:
    obsidian_path = settings.get_note_path(
        state["message_thread"],
        state["created_at"],
    )

    # Проверяем существует ли файл/папка obsidian
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)

    # Формируем контент
    body = add_task_fields(state)
    # если файл не существует:
    if not obsidian_path.exists():
        frontmatter = get_frontmatter(state)
        full_content = frontmatter + "\n\n" + body
        return create_file(obsidian_path, full_content)
    # если файл существует:
    else:
        if state.get("tags") or state.get("people_mentioned"):
            return add_frontmatter_fields(
                obsidian_path,
                state.get("tags") or [],
                state.get("people_mentioned") or [],
                body,
            )
        else:
            return add_to_file(obsidian_path, "\n\n" + body)


async def db_updater(state: FamilyAtlasState, config: RunnableConfig) -> dict:
    session = config["configurable"]["session"]
    embedding_model = config["configurable"]["embedding_model"]
    embedding = embedding_model.encode(state.get("summary")).tolist()

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
                obsidian_path=state.get("obsidian_path"),
                embedding=embedding,
                status="done",
            )
        )
        await session.commit()
        logger.info(
            f'Assembled сообщение {state["session_id"]} сохранено в БД'
        )
    except Exception as e:
        logger.error(
            f"Во время сохранения обработанного assembled сообщения в БД произошла ошибка {e}"
        )
        await session.execute(
            update(AssembledMessages)
            .where(AssembledMessages.session_id == state["session_id"])
            .values(status="error")
        )
        await session.commit()

    return {}


def get_candidate_summaries(
    candidates_idxs: set[int], session_ids: list[int], summaries: list[str]
) -> list[dict]:
    candidates = [
        {"session_id": session_ids[idx], "session_summary": summaries[idx]}
        for idx in candidates_idxs
    ]
    return candidates


async def find_relatives(
    state: FamilyAtlasState, config: RunnableConfig
) -> dict:
    if not state.get("summary"):
        return {"related": []}

    session = config["configurable"]["session"]

    session_ids, summaries, obsidian_paths, embeddings = await get_summaries(session)
    if not summaries:
        return {"related": []}

    embedding_model = config["configurable"]["embedding_model"]

    # здесь получаем релевантные индексы соответствующие session_ids и obsidian_paths
    # важно: индексы ищутся через UNION bm25 и embeddings результатов.
    # Позже, когда будет много заметок можно изменить логику поиска релевантных индексов
    candidates_idxs = find_candidates(
        state["summary"], summaries, embeddings,  morph, embedding_model
    )
    if not candidates_idxs:
        return {"related": []}

    llm = config["configurable"]["llm"]
    system_prompt, pdtc_output = choose_state("find_relatives")
    # Фирмируем системное сообщение
    system_msg = SystemMessage(content=system_prompt)
    candidates = get_candidate_summaries(
        candidates_idxs, session_ids, summaries
    )
    # Фирмируем сообщение пользователя
    hum_msg = HumanMessage(content=(
        f"Summary исходного сообщения:\n{state['summary']}\n\n"
        f"Список кандидатов для сравнения:\n{candidates}"
    ))
    # задаем pydantic схему для LLM вывода
    structured_llm = llm.with_structured_output(pdtc_output)
    result_ids = await structured_llm.ainvoke([system_msg, hum_msg])
    if not result_ids.session_ids:
        return {"related": []}

    related = []
    for sid in result_ids.session_ids:
        if sid in session_ids:
            idx = session_ids.index(sid)
            related.append(f'{Path(obsidian_paths[idx]).stem}')

    logger.info(f"find_relatives: найдено {len(related)} связанных заметок для session_id={state['session_id']}")
    return {"related": related}