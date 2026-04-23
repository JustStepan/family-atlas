from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

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


async def diary_note_file_writer(state: FamilyAtlasState) -> dict:
    # write this fields into obsidian vault 
    obsidian_path = settings.get_note_path(
        state["message_thread"],
        state["created_at"],
        state["title"]
    )
    # Проверяем существует ли файл/папка obsidian
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Формируем содержание файла
    tags_yaml = "\n".join(f"  - {tag}" for tag in state["tags"])
    people = state.get("people_mentioned") or []
    people_yaml = "\n".join(f"  - {p}" for p in people)

    frontmatter = (
        "---\n"
        f"author: {state['author_name']}\n"
        f"created: {state['created_at']}\n"
        f"thread: {state['message_thread']}\n"
        f"tags:\n{tags_yaml}\n"
        f"people_mentioned:\n{people_yaml}\n"
        "related: []\n"
        "---"
    )

    body = f"# {state['title']}\n\n{state['content']}"

    attachments = state.get("attachments") or []
    if attachments:
        links = "\n".join(f"![[{Path(p).name}]]" for p in attachments)
        body += f"\n\n## Вложения\n{links}"
    
    full_content = frontmatter + "\n\n" + body

    # пробуем записать файл 
    try:
        if obsidian_path.exists():
            logger.warning(f"Файл уже существует: {obsidian_path}")
            return {"obsidian_path": str(obsidian_path), "status": "exists"}

        obsidian_path.write_text(full_content, encoding="utf-8")
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

    # входные — обязательные
    # session_id: int
    # message_thread: str
    # raw_content: str
    # created_at: str
    # author_name: strа
    # title: NotRequired[str]
    # summary: NotRequired[str]
    # content: NotRequired[str]
    # tags: NotRequired[list[str]]
    # people_mentioned: NotRequired[list[str]]
    # obsidian_path: NotRequired[str]
    # status: NotRequired[str]
    pass


async def calendar_file_writer(state: FamilyAtlasState) -> dict:
    # write this fields into obsidian vault
    # title: NotRequired[str]
    # summary: NotRequired[str]
    # content: NotRequired[str]
    # tags: NotRequired[list[str]]
    # people_mentioned: NotRequired[list[str]]
    # obsidian_path: NotRequired[str]
    # status: NotRequired[str]
    # +++
    # event_time: NotRequired[str]
    # event_end_time: NotRequired[str | None]
    # location: NotRequired[str | None]
    pass

async def task_file_writer(state: FamilyAtlasState) -> dict:
    # write this fields into obsidian vault



    # title: NotRequired[str]
    # summary: NotRequired[str]
    # content: NotRequired[str]
    # tags: NotRequired[list[str]]
    # people_mentioned: NotRequired[list[str]]
    # obsidian_path: NotRequired[str]
    # status: NotRequired[str]
    # +++
    # deadline: NotRequired[str | None]
    # is_done: NotRequired[bool]
    # priority: NotRequired[str | None]
    pass

async def db_writer(state: FamilyAtlasState) -> dict:
    # здесь происходит запись данных в базу данных
    pass

async def find_ralatives(state: FamilyAtlasState) -> dict:
    # stage 3 - поиск родственных заметок. 
    # Через tags, bm25, embeddings
    pass