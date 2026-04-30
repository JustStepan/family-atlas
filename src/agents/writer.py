from pathlib import Path
from sqlalchemy import update

from src.agents.nodes import (
    get_frontmatter,
    create_file,
    add_frontmatter_fields,
    add_to_file,
    add_task_fields,
    add_addition_calend_fields,
)
from src.config import settings
from src.database.models import AssembledMessages
from src.logger import logger


async def write_note(msg: dict, session) -> str:
    state = msg
    thread = msg["message_thread"]

    try:
        if thread == "task":
            result = await _write_task(state)
        else:
            result = await _write_diary_note_calend(state)

        new_status = result.get("status", "error")
        # "written" и "exists" считаем успехом
        final_status = "done" if new_status in ("written", "exists", "rewritten") else "error"

    except Exception as e:
        logger.error(f"Ошибка записи сессии {msg.session_id}: {e}")
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

    frontmatter = get_frontmatter(state)
    body = f"# {state['title']}\n\n{state['content']}"

    if calend_additions := add_addition_calend_fields(state):
        body += calend_additions

    if attachments := state.get("attachments"):
        links = "\n".join(f"![[{Path(p).name}]]" for p in attachments)
        body += f"\n\n## Вложения\n{links}"

    return create_file(obsidian_path, frontmatter + "\n\n" + body)


async def _write_task(state: dict) -> dict:
    obsidian_path = settings.get_note_path(
        state["message_thread"], state["created_at"]
    )
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)
    body = add_task_fields(state)

    if not obsidian_path.exists():
        frontmatter = get_frontmatter(state)
        return create_file(obsidian_path, frontmatter + "\n\n" + body)
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