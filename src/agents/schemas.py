from pydantic import BaseModel, Field


class TextSummarizerOutput(BaseModel):
    summary: str = Field(description="Суммаризация представленного текста")
    tags: str = Field(description="Теги для представленного текста")
