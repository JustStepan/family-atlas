from datetime import datetime
from pathlib import Path

import frontmatter as fm
from sqlalchemy import update

from src.agents.schemas import PersonInfo
from src.config import settings
from src.database.models import AssembledMessages
from src.logger import logger
from src.integrations.google_calendar import create_calendar_event


def person_to_wikilink(name: str) -> str:
    """Возвращает wikilink вида [[persons/Имя]] или [[Имя]] если уже в скобках."""
    if name.startswith("[["):
        return name
    return f"[[persons/{name}]]"


def get_frontmatter(state: dict) -> str:
    tags_yaml = "\n".join(f"  - {tag}" for tag in state["tags"])
    people = state.get("people_mentioned") or []
    people_yaml = "\n".join(f'  - "{person_to_wikilink(p["name"])}"' for p in people)
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

def create_person_file(person: dict[str, str], created_at: str, note_stem: str) -> dict:
    person_path = settings.persons_path / f"{person['name']}.md"
    settings.persons_path.mkdir(parents=True, exist_ok=True)

    post = fm.Post(
        content=(
            f"## {created_at[:10]}\n"
            f"{person['context']}\n"
            f"[[{note_stem}]]"
        ),
        **{
            "name": person['name'],
            "role": person['relation'],
            "first_seen": created_at[:10],
            "last_seen": created_at[:10],
            "mentioned_in": [f"[[{note_stem}]]"],
        }
    )

    try:
        person_path.write_text(fm.dumps(post), encoding="utf-8")
        logger.info(f"Файл {person_path.name} успешно записан в хранилище")
        return {"obsidian_path": str(person_path), "status": "written"}
    except Exception as e:
        logger.error(f"Во время записи файла персоны произошла ошибка: {e}")
        return {"obsidian_path": str(person_path), "status": "error"}


def update_person_file(db_person, person: PersonInfo, created_at: str, note_stem: str) -> None:
    person_path = Path(db_person.obsidian_path)
    if not person_path.exists():
        logger.warning(f"Файл персоны не найден: {person_path}")
        return

    post = fm.load(person_path)
    
    # Обновляем mentioned_in во frontmatter
    mentioned = post.get("mentioned_in") or []
    wikilink = f"[[{note_stem}]]"
    if wikilink not in mentioned:
        mentioned.append(wikilink)
    post["mentioned_in"] = mentioned
    post["last_seen"] = created_at[:10]

    # Дописываем новый блок
    post.content += (
        f"\n\n### {created_at[:10]}\n"
        f"{person["context"]}\n"
        f"[[{note_stem}]]"
    )

    with open(person_path, "w", encoding="utf-8") as f:
        f.write(fm.dumps(post))
    logger.info(f"Файл персоны обновлен: {person_path.name}")


def add_addition_calend_fields(state: dict) -> str:
    add_str = ""
    if state.get("event_time"):
        add_str += f"\n\n---\nВремя события: {state.get('event_time')}"
    if state.get("location"):
        add_str += f", Место события: {state.get('location')}"
    return add_str


def add_frontmatter_fields(
    obsidian_path: Path, tags: list[str], people: list[dict], body: str
) -> dict:
    post = fm.load(obsidian_path)
    post["tags"] = list(set((post.get("tags") or []) + tags))
    post["people_mentioned"] = list(
        set(
            (post.get("people_mentioned") or [])
            + [person_to_wikilink(p["name"]) for p in people]
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
    google_calendar_link = None
    try:
        if thread == "task":
            result = await _write_task(msg)
        else:
            result = await _write_diary_note_calend(msg)
        new_status = result.get("status", "error")
        final_status = "done" if new_status in ("written", "exists", "rewritten") else "error"
        google_calendar_link = result.get("google_calendar_link")
    except Exception as e:
        logger.error(f"Ошибка записи сессии {msg['session_id']}: {e}")
        final_status = "error"

    values = {"status": final_status}
    if google_calendar_link:
        values["google_calendar_link"] = google_calendar_link

    await session.execute(
        update(AssembledMessages)
        .where(AssembledMessages.session_id == msg["session_id"])
        .values(**values)
    )
    await session.commit()
    return final_status


def update_related_notes(current_stem: str, related: list[str]) -> None:
    """Обновляет frontmatter связанных заметок — добавляет текущую заметку в их related."""
    for stem in related:
        matches = list(settings.OBSIDIAN_VAULT_PATH.rglob(f"{stem}.md"))
        if not matches:
            logger.warning(f"update_related_notes: файл не найден для стема '{stem}'")
            continue

        note_path = matches[0]
        try:
            post = fm.load(note_path)
            existing_related = post.get("related") or []
            wikilink = f"[[{current_stem}]]"
            if wikilink not in existing_related:
                existing_related.append(wikilink)
                post["related"] = existing_related
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(fm.dumps(post))
                logger.info(f"update_related_notes: добавлена связь {wikilink} → {note_path.name}")
        except Exception as e:
            logger.error(f"update_related_notes: ошибка обновления {note_path.name}: {e}")

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

    result = create_file(obsidian_path, get_frontmatter(state) + "\n\n" + body)

    # Обновляем связанные заметки
    if result.get("status") == "written" and state.get("related"):
        current_stem = obsidian_path.stem
        update_related_notes(current_stem, state["related"])

    # Google Calendar — только для calendar треда
    if state["message_thread"] == "calendar" and state.get("event_time"):
        gcal_link = create_calendar_event(
            title=state["title"],
            event_time=state["event_time"],
            event_end_time=state.get("event_end_time"),
            description=state.get("summary"),
        )
        if gcal_link:
            result["google_calendar_link"] = gcal_link
            # дописываем ссылку в уже созданный файл
            with open(obsidian_path, "a", encoding="utf-8") as f:
                f.write(f"\n[📅 Открыть в Google Calendar]({gcal_link})\n")

    return result

async def _write_task(state: dict) -> dict:
    obsidian_path = settings.get_note_path(
        state["message_thread"], state["created_at"]
    )
    obsidian_path.parent.mkdir(parents=True, exist_ok=True)
    body = add_task_fields(state)

    if not obsidian_path.exists():
        result = create_file(obsidian_path, get_frontmatter(state) + "\n\n" + body)
    elif state.get("tags") or state.get("people_mentioned"):
        result = add_frontmatter_fields(
            obsidian_path,
            state.get("tags") or [],
            state.get("people_mentioned") or [],
            body,
        )
    else:
        result = add_to_file(obsidian_path, "\n\n" + body)

    if result.get("status") in ("written", "rewritten") and state.get("related"):
        update_related_notes(obsidian_path.stem, state["related"])

    return result


def write_summary_note(period_start: str, period_end: str, content: str) -> dict:
    """summary/YYYY/MM-месяц/WW-неделя.md"""
    from src.config import MONTH_NAMES
    start = datetime.strptime(period_start, "%Y-%m-%d")
    week = start.isocalendar()[1]
    month_dir = f"{start.strftime('%m')}-{MONTH_NAMES[start.strftime('%m')]}"
    path = settings.summary_path / start.strftime("%Y") / month_dir / f"{week}-неделя.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    body = (
        f"---\nperiod: {period_start} — {period_end}\ntype: weekly_summary\n---\n\n"
        f"# Сводка за неделю {week} ({period_start} — {period_end})\n\n{content}"
    )
    return create_file(path, body)