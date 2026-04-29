from typing import NotRequired, TypedDict

from pydantic import BaseModel, Field

import src.prompts.assembler_prompts as agent_prompt


class FamilyAtlasState(TypedDict):
    # входные — обязательные
    session_id: int
    message_thread: str
    raw_content: str
    created_at: str
    author_name: str
    attachments: list[str]
    # выходные — опциональные (заполняются узлами)
    title: NotRequired[str]
    related: NotRequired[list[str]]
    summary: NotRequired[str]
    content: NotRequired[str]
    tags: NotRequired[list[str]]
    people_mentioned: NotRequired[list[str]]
    obsidian_path: NotRequired[str]
    status: NotRequired[str]
    # calendar-specific
    event_time: NotRequired[str]
    event_end_time: NotRequired[str | None]
    location: NotRequired[str | None]
    # task-specific
    deadline: NotRequired[str | None]
    is_done: NotRequired[bool]
    priority: NotRequired[str | None]


class AudioNormalizer(BaseModel):
    """Модель для получения нормализованного текста аудиосообщений"""
    content: str = Field(description="Результат нормализации текста, транскрибированного из аудио сообщения. Выполнено согласно промпта")


class RelatedNotesFinder(BaseModel):
    """Модель для получения id заметок/сессий по суммари"""
    session_ids: list[int] = Field(description="Результат сравнения summary исходной заметки и session_summary других заметок. Возвращаются только номера id связанных заметок")


class SessionBaseOutput(BaseModel):
    """Базовая модель получения финальных данных из ассемблированных сессий
    На вход подается assembled messages соответствующей модели"""

    title: str = Field(description="Краткий и емкий заголовок для текста")
    summary: str = Field(
        description="Краткая суммаризация текста. Только факты из текста, без домыслов."
    )
    content: str = Field(
        description=(
            "Итоговый текст в формате Markdown. "
            "Без технических метаданных (дат, идентификаторов). "
            "Если документ без содержимого — только название файла и тип, без домыслов."
        )
    )
    tags: list[str] = Field(
        description=(
            "Список тегов. Правила: "
            "каждый тег начинается с #, "
            "слова разделяются underscore: #word1_word2, "
            "минимум 2, максимум 6 тегов."
        )
    )
    people_mentioned: list[str] | None = Field(
        description=(
            "Список персон упомянутых в тексте. "
            "Имена нормализуются до именительного падежа. "
            "Если персоналий нет — пустой список []."
        )
    )


class SessionCalendarOutput(SessionBaseOutput):
    """Модель получения данных для календарных записей"""
    event_time: str = Field(description="Время начала события в формате ISO: '2026-04-20 15:00'")
    event_end_time: str | None = Field(description="Время окончания события")
    location: str | None = Field(description="Место проведения события")
    is_recurring: bool = Field(
        description="True если событие повторяется регулярно (еженедельно, ежемесячно и т.д.), иначе False"
    )
    google_calendar_link: str | None = Field(
        description="Ссылка на Google календарь"
    )


class SessionTaskOutput(SessionBaseOutput):
    """Модель получения данных для задач"""
    deadline: str | None = Field(description="Срок исполнения задания")
    is_done: bool = Field(description="Выполнено ли описываемое задание")
    priority: str | None = Field(
        description="Приоритет задания: low, medium, high. Если не указан явно — None"
    )


SESSION_PROMPT_MAP = {
    "notes":    (agent_prompt.NOTES_PROMPT,    SessionBaseOutput),
    "diary":    (agent_prompt.DIARY_PROMPT,    SessionBaseOutput),
    "calendar": (agent_prompt.CALENDAR_PROMPT, SessionCalendarOutput),
    "task":     (agent_prompt.TASK_PROMPT,     SessionTaskOutput),
    "find_relatives": (agent_prompt.FIND_RELATIVES, RelatedNotesFinder)
}


def choose_state(thread_type: str) -> tuple[str, BaseModel]:
    state = SESSION_PROMPT_MAP.get(thread_type, None)
    if not state:
        raise ValueError('Проверьте тип передаваемого треда')
    return SESSION_PROMPT_MAP[thread_type]
