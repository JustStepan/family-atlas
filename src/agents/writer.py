from pathlib import Path

import frontmatter as fm
from sqlalchemy import update

from src.config import settings
from src.database.models import AssembledMessages
from src.logger import logger


def person_to_wikilink(name: str) -> str:
    if name.startswith("[["):
        return f'"{name}"'
    return f'"[[persons/{name}]]"'


def get_frontmatter(state: dict) -> str:
    tags_yaml = "\n".join(f"  - {tag}" for tag in state["tags"])
    people = state.get("people_mentioned") or []
    people_yaml = "\n".join(f"  - {person_to_wikilink(p)}" for p in people)
    related = state.get("related") or []
    related_yaml = "\n".join(f'  - "[[{r}]]"' for r in related)
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


def add_addition_calend_fields(state: dict) -> str:
    add_str = ""
    if state.get("event_time"):
        add_str += f"\n---\nВремя события: {state.get('event_time')}"
    if state.get("location"):
        add_str += f", Место события: {state.get('location')}"
    return add_str


def add_frontmatter_fields(
    obsidian_path: Path, tags: list[str], people: list[str], body: str
) -> dict:
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
            logger.info(f"Задача добавлена в существующий файл: {obsidian_path.name}")
            return {"obsidian_path": str(obsidian_path), "status": "rewritten"}
    except Exception as e:
        logger.error(f"Во время добавления контента к файлу произошла ошибка: {e}")
        return {"obsidian_path": str(obsidian_path), "status": "error"}


def add_to_file(obsidian_path: Path, content: str) -> dict:
    try:
        with open(obsidian_path, "a", encoding="utf-8") as f:
            f.write(content)
            return {"obsidian_path": str(obsidian_path), "status": "written"}
    except Exception as e:
        logger.error(f"Во время добавления контента к файлу произошла ошибка: {e}")
        return {"obsidian_path": str(obsidian_path), "status": "error"}


def add_task_fields(state: dict) -> str:
    checkbox = "- [x]" if state.get("is_done") else "- [ ]"
    body = f'\n{checkbox} **{state["title"]}**'
    if state.get("deadline"):
        body += f'\n📅 Дедлайн: {state["deadline"]}'
    if state.get("priority"):
        body += f'\n⚡ Приоритет: {state["priority"]}'
    body += f"\n{state['content']}"
    if attachments := state.get("attachments") or []:
        links = "\n".join(f"![[{Path(p).name}]]" for p in attachments)
        body += f"\n\n### Вложения\n{links}"
    return body + "\n\n---"


async def write_note(msg: dict, session) -> str:
    thread = msg["message_thread"]
    try:
        if thread == "task":
            result = await _write_task(msg)
        else:
            result = await _write_diary_note_calend(msg)
        new_status = result.get("status", "error")
        final_status = "done" if new_status in ("written", "exists", "rewritten") else "error"
    except Exception as e:
        logger.error(f"Ошибка записи сессии {msg['session_id']}: {e}")
        final_status = "error"

    await session.execute(
        update(AssembledMessages)
        .where(AssembledMessages.session_id == msg["session_id"])
        .values(status=final_status)
    )
    await session.commit()
    return final_status


async def _write_diary_note_calend(state: dict) -> dict:
    obsidian_path = settings.get_note_path(
        state["message_thread"], state["created_at"], state["title"]
    )
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)
    body = f"# {state['title']}\n\n{state['content']}"
    if calend_additions := add_addition_calend_fields(state):
        body += calend_additions
    if attachments := state.get("attachments"):
        links = "\n".join(f"![[{Path(p).name}]]" for p in attachments)
        body += f"\n\n## Вложения\n{links}"
    return create_file(obsidian_path, get_frontmatter(state) + "\n\n" + body)


async def _write_task(state: dict) -> dict:
    obsidian_path = settings.get_note_path(
        state["message_thread"], state["created_at"]
    )
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)
    body = add_task_fields(state)
    if not obsidian_path.exists():
        return create_file(obsidian_path, get_frontmatter(state) + "\n\n" + body)
    if state.get("tags") or state.get("people_mentioned"):
        return add_frontmatter_fields(
            obsidian_path,
            state.get("tags") or [],
            state.get("people_mentioned") or [],
            body,
        )
    return add_to_file(obsidian_path, "\n\n" + body)