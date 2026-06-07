import re
import unicodedata

from rapidfuzz import fuzz
from sqlalchemy import select

from src.database.models import Person
from src.config import settings

# Инвертированный словарь семьи строим один раз: {норм_алиас: (имя, роль)}
_family_map: dict[str, tuple[str, str | None]] | None = None


def _normalize(name: str, morph) -> str:
    """Ключ для сравнения. Важна не лингвистическая верность, а идемпотентность:
    обе сравниваемые строки прогоняются одинаково — значит, совпадут."""
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"[()«»\"'.,]", " ", name)  # скобки/кавычки/точки -> пробел
    tokens = [morph.parse(t)[0].normal_form for t in name.lower().split()]
    return " ".join(tokens)


def _get_family_map(morph) -> dict[str, tuple[str, str | None]]:
    global _family_map
    if _family_map is None:
        _family_map = {}
        for raw_key, aliases in settings.FAMILY_ALIASES.items():
            name, _, role = raw_key.partition("|")  # partition не падает без разделителя
            for alias in aliases:
                _family_map[_normalize(alias, morph)] = (name, role or None)
    return _family_map


async def _load_person_names(session) -> list[str]:
    q = await session.execute(select(Person.name))
    return list(q.scalars().all())


async def _person_exists(session, name: str) -> bool:
    q = await session.execute(select(Person.id).where(Person.name == name))
    return q.scalar_one_or_none() is not None


async def resolve_person(mention: dict, session, morph) -> dict:
    """Решает судьбу упоминания БЕЗ LLM.
    Возврат: {"action": "link"|"create"|"skip", "canonical_name": str, "role": str|None}
    """
    raw_name = (mention.get("name") or "").strip()
    if not raw_name:
        return {"action": "skip", "canonical_name": "", "role": None}

    key = _normalize(raw_name, morph)
    role = mention.get("relation")

    # 1. Семья (.env) — высший приоритет, гейт пропускаем
    family = _get_family_map(morph)
    if key in family:
        canonical, fam_role = family[key]
        action = "link" if await _person_exists(session, canonical) else "create"
        return {"action": action, "canonical_name": canonical, "role": fam_role}

    # 2. Совпадение с персонами в БД: точное по ключу + нечёткое
    for db_name in await _load_person_names(session):
        if key == _normalize(db_name, morph) or \
           fuzz.token_sort_ratio(key, _normalize(db_name, morph)) >= settings.PERSON_FUZZY_THRESHOLD:
            return {"action": "link", "canonical_name": db_name, "role": role}

    # 3. Новый человек. Гейт: фамилия (>=2 слов) ИЛИ явная роль
    if len(key.split()) >= 2 or role:
        return {"action": "create", "canonical_name": raw_name, "role": role}

    # 4. Одиночное имя без роли — не заводим
    return {"action": "skip", "canonical_name": raw_name, "role": None}