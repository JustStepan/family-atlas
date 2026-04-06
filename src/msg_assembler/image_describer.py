from datetime import datetime
from pathlib import Path
import base64
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.msg_assembler.schemas import VisionOutput
from src.prompts.vision import VISION_SYSTEM_MSG
from src.infrastructure.context import AppContext
from src.config import settings

from src.msg_assembler.telegram_file import download_file
from src.database.models import LocalRawMessages
from src.logger import logger


MEDIA_DIR = settings.get_media_path('images')
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def image_to_base64(filepath: Path) -> str:
    with open(filepath, 'rb') as f:
        base64_bytes = base64.b64encode(f.read())
        base64_string = base64_bytes.decode('ascii')
        return base64_string


async def image_describer(filepath: Path, msg_caption: str) -> dict:
    async with AppContext(verbose=False) as ctx:
        await ctx.use_model("vision")
        bs64_string = image_to_base64(filepath)
        return await describe_image(ctx.llm, bs64_string, msg_caption)


async def describe_image(llm: ChatOpenAI, bs64: str, msg_caption: str) -> dict:
    caption_string = f"\nПервоначальный заголовок предоставленного изображения: '{msg_caption}'"
    system_msg = SystemMessage(content=VISION_SYSTEM_MSG)
    hum_message = HumanMessage(content=[
        {"type": "image_url",
         "image_url": {"url": f"data:image/jpeg;base64,{bs64}"}},
        {"type": "text", "text": f"Опиши что на фотографии и сделай/обнови заголовок.{caption_string}"}
    ])

    structured_llm = llm.with_structured_output(VisionOutput)
    return await structured_llm.ainvoke([system_msg, hum_message])


def rename_file(old_path: Path, new_name: str) -> Path:
    name = "_".join([n.strip() for n in new_name.split()])
    name = re.sub(r'[^\w]', '_', name)
    if not name:
        name = f'Файл_от_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
    new_path = old_path.parent / f'{name}{old_path.suffix}'
    old_path.rename(new_path)
    return new_path


async def process_photo_messages(
        photo_msgs: list[LocalRawMessages],
        extension: str = "jpeg"
        ) -> list[LocalRawMessages]:
    """Функция описания фото из базы данных."""

    for msg in photo_msgs:
        msg_caption = msg.caption if msg.caption else ''

        try:
            logger.info(f"Обрабатываем фото сообщение {msg.id}...")

            photo_path = await download_file(msg.file_id, MEDIA_DIR, extension)
            vision_response = await image_describer(photo_path, msg_caption)

            logger.info(f"Получено описание для сообщения {msg.id}: {vision_response.description[:50]}...")
            # Переименовываем
            new_path = rename_file(photo_path, vision_response.caption)
            msg.file_path = str(new_path)

            msg.caption = vision_response.caption
            # формируем контент правильно
            if msg.forwarded_msg_info and msg.content:
                prev_cont = "Содержание пересланного сообщения: " + msg.content
                photo_content = "\nОписание прикрепленного фото из пересланного сообщения: " + vision_response.description
                msg.content = prev_cont + photo_content
            else:
                msg.content = vision_response.description
            msg.msg_status = "described"

        except Exception as e:
            logger.error(f"Ошибка распознования: {e}")
            msg.msg_status = "error_photo_describing"

    return photo_msgs
