from pydantic import BaseModel, Field


class TextSummarizerOutput(BaseModel):
    summary: str = Field(
        description="Краткая суммаризация текста. Только факты из текста, без домыслов."
    )
    tags: list[str] = Field(
        description=(
            "Список тегов. Правила: "
            "каждый тег начинается с #, "
            "слова разделяются underscore: #word1_word2, "
            "минимум 2, максимум 6 тегов."
        )
    )
    content: str = Field(
        description=(
            "Итоговый текст в формате Markdown. "
            "Без технических метаданных (дат, идентификаторов). "
            "Если документ без содержимого — только название файла и тип, без домыслов."
        )
    )