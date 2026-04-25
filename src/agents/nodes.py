from pathlib import Path

import frontmatter as fm
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy import update

from src.database.models import AssembledMessages
from src.database.utils import get_existing_tags, get_known_persons
from src.agents.schemas import FamilyAtlasState, choose_state
from src.logger import logger
from src.config import settings


async def assembld_text_analyzer(state: FamilyAtlasState, config: RunnableConfig) -> dict:
    logger.info(f"Начинаем обра,отку сессии: {state["session_id"]} - {state["message_thread"]}")

    tread_type = state["message_thread"]
    system_prompt, pdtc_output = choose_state(tread_type)
    thread_content = state["raw_content"]
    
    llm = config["configurable"]["llm"]
    session = config["configurable"]["session"]

    existing_tags = await get_existing_tags(session)
    known_persons = await get_known_persons(session)
    logger.info(f"Передаем на обработку существующие теги ({len(existing_tags)} шт.) и персоналии ({len(known_persons)} шт.)")

    created_at = state["created_at"]

    context = f"\nСуществующие теги: {', '.join(existing_tags)}"
    context += f"\nИзвестные персоны: {', '.join(known_persons)}"
    hum_msg = HumanMessage(content=(
        f"Автор сообщения: {state['author_name']} — не включай его в people_mentioned\n"
        f"Обработай текст:\n{thread_content}\n"
        f"Время: {created_at}\n{context}"
    ))
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
    logger.info(f"Функция 'thread_router'. Session: {state["session_id"]} - {state["message_thread"]}")
    return state["message_thread"]


def get_frontmatter(state: FamilyAtlasState) -> str:
    tags_yaml = "\n".join(f"  - {tag}" for tag in state["tags"])
    people = state.get("people_mentioned") or []
    people_yaml = "\n".join(f"  - {p}" for p in people)
    related = state.get('related') or []
    related_yaml = "\n".join(f"  - \"[[{Path(r).stem}]]\"" for r in related)

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
        return {
            "obsidian_path": str(obsidian_path),
            "status": "written"
        }
    except Exception as e:
        logger.error(f"Во время записи файла произошла ошибка: {e}")
        return {
            "obsidian_path": str(obsidian_path),
            "status": "error"
        }

async def diary_note_calend_file_writer(state: FamilyAtlasState) -> dict:
    # write this fields into obsidian vault 
    obsidian_path = settings.get_note_path(
        state["message_thread"],
        state["created_at"],
        state["title"]
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
    add_str = ''
    if state.get('event_time'):
        add_str += f'\n---\nВремя события: {state.get('event_time')}'
    if state.get('location'):
        add_str += f', Место события: {state.get('location')}'
    return add_str


def add_frontmatter_fields(obsidian_path: Path, tags: list[str], people: list[str], body):
    post = fm.load(obsidian_path)
    post["tags"] = list(set((post.get("tags") or []) + tags))
    post["people_mentioned"] = list(set((post.get("people_mentioned") or []) + people))
    post.content += "\n\n" + body

    try:
        with open(obsidian_path, "w", encoding="utf-8") as f:
            fm.dump(post, f)
            return {
                "obsidian_path": str(obsidian_path),
                "status": "rewritten"
            }
    except Exception as e:
        logger.error(f"Во время добавления контента к файлу произошла ошибка: {e}")
        return {
            "obsidian_path": str(obsidian_path),
            "status": "error"
        }


def add_to_file(obsidian_path, content) -> dict:
    try:
        with open(obsidian_path, "a") as f:
            f.write(content)
            return {
                "obsidian_path": str(obsidian_path),
                "status": "written"
            }
    except Exception as e:
        logger.error(f"Во время добавления контента к файлу произошла ошибка: {e}")
        return {
            "obsidian_path": str(obsidian_path),
            "status": "error"
        }


async def task_file_writer(state: FamilyAtlasState) -> dict:
    obsidian_path = settings.get_note_path(
        state["message_thread"],
        state["created_at"],
    )

    # Проверяем существует ли файл/папка obsidian
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)

    # Формируем контент
    body = f"# {state['title']}\n\n{state['summary']}"
    if attachments := state.get("attachments") or []:
        links = "\n".join(f"![[{Path(p).name}]]" for p in attachments)
        body += f"\n\n## Вложения\n{links}"

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
                body
            )
        else:
            return add_to_file(obsidian_path, "\n\n" + body)


async def db_updater(state: FamilyAtlasState, config: RunnableConfig) -> dict:
    session = config["configurable"]["session"]

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
                status="done",
            )
        )
        await session.commit()
        logger.info(f'Assembled сообщение {state["session_id"]} сохранено в БД')
    except Exception as e:
        logger.error(f'Во время сохранения обработанного assembled сообщения в БД произошла ошибка {e}')
        await session.execute(
            update(AssembledMessages)
            .where(AssembledMessages.session_id == state["session_id"])
            .values(status="error")
        )

    return {}


async def find_ralatives(state: FamilyAtlasState) -> dict:
    """Заглушка с тестовой заметкой"""
    return {"related": ['/Users/stepan/Documents/Obsidian_test_vault/Test_note.md']}