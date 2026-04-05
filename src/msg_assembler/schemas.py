from pydantic import BaseModel, Field


class VisionOutput(BaseModel):
    caption: str = Field(description="Заголовок изображения")
    description: str = Field(description="Описание изображения")