from pathlib import Path

import frontmatter as fm
from sqlalchemy import select

from src.database.models import AssembledMessages, Person
from src.config import settings
from src.logger import logger


async def merge_persons(session, source_name: str, target_name: str) -> dict:
    """Сливает source в target: данные БД + файлы Obsidian. source удаляется."""
    if source_name == target_name:
        return {"msg": "Нельзя слить персону саму с собой"}

    source = (await session.execute(
        select(Person).where(Person.name == source_name))).scalar_one_or_none()
    target = (await session.execute(
        select(Person).where(Person.name == target_name))).scalar_one_or_none()
    if not source or not target:
        return {"msg": "Одна из персон не найдена"}

    # 1. Переносим данные в target. ВАЖНО: присваиваем новые объекты, а не мутируем —
    #    иначе SQLAlchemy не заметит изменения JSON-полей.
    target.mentioned_in = list(dict.fromkeys((target.mentioned_in or []) + (source.mentioned_in or [])))
    target.contexts = list(dict.fromkeys((target.contexts or []) + (source.contexts or [])))
    target.first_seen = min(target.first_seen, source.first_seen)
    target.last_seen = max(target.last_seen, source.last_seen)

    # 2. Чиним people_mentioned во всех заметках: source -> target + дедуп
    notes = (await session.execute(
        select(AssembledMessages).where(AssembledMessages.people_mentioned.isnot(None))
    )).scalars().all()
    fixed = 0
    for note in notes:
        people = note.people_mentioned or []
        if not any(p.get("name") == source_name for p in people):
            continue
        seen, deduped = set(), []
        for p in people:
            name = target_name if p.get("name") == source_name else p.get("name")
            if name not in seen:
                seen.add(name)
                deduped.append({**p, "name": name})
        note.people_mentioned = deduped  # присваивание -> изменение зафиксируется
        fixed += 1

    source_path = source.obsidian_path
    await session.delete(source)
    await session.commit()
    logger.info(f"merge: БД {source_name} -> {target_name}, заметок исправлено: {fixed}")

    files_log = _merge_files(source_name, target_name, source_path, target.obsidian_path)
    return {"msg": f"{source_name} → {target_name}. Заметок: {fixed}. {files_log}"}


def _merge_files(source_name, target_name, source_path, target_path) -> str:
    msgs = []
    src_file = Path(source_path) if source_path else settings.persons_path / f"{source_name}.md"
    tgt_file = Path(target_path) if target_path else settings.persons_path / f"{target_name}.md"

    # 2a. содержимое карточки source -> в target, затем удаляем файл source
    try:
        if src_file.exists() and tgt_file.exists():
            src_post, tgt_post = fm.load(src_file), fm.load(tgt_file)
            tgt_post["mentioned_in"] = list(dict.fromkeys(
                (tgt_post.get("mentioned_in") or []) + (src_post.get("mentioned_in") or [])
            ))
            tgt_post.content += f"\n\n{src_post.content}"
            tgt_file.write_text(fm.dumps(tgt_post), encoding="utf-8")
        if src_file.exists():
            src_file.unlink()
            msgs.append("карточка удалена")
    except Exception as e:
        logger.error(f"merge: ошибка карточек: {e}")
        msgs.append(f"ошибка карточек: {e}")

    # 2b. перецепляем вики-ссылки по всему vault
    old, new = f"[[persons/{source_name}]]", f"[[persons/{target_name}]]"
    relinked = 0
    for note_path in settings.OBSIDIAN_VAULT_PATH.rglob("*.md"):
        try:
            text = note_path.read_text(encoding="utf-8")
            if old in text:
                note_path.write_text(text.replace(old, new), encoding="utf-8")
                relinked += 1
        except Exception as e:
            logger.error(f"merge: ошибка ссылки в {note_path.name}: {e}")
    msgs.append(f"ссылок перецеплено: {relinked}")
    logger.info(f"merge: файлы — {', '.join(msgs)}")
    return ", ".join(msgs)