from pathlib import Path
import mimetypes
from datetime import datetime
import re

from src.infrastructure.context import AppContext
from src.msg_assembler.image_describer import process_photo_messages
from src.msg_assembler.voice_recognition import process_voice_messages
from src.config import settings

from src.database.models import LocalRawMessages
from src.logger import logger


DOC_DIR = settings.get_media_path('docs')
DOC_DIR.mkdir(parents=True, exist_ok=True)


MIME_TO_HANDLER = {
    'image/jpeg': process_photo_messages,
    'image/png':  process_photo_messages,
    'image/webp': process_photo_messages,
    'image/gif':  process_photo_messages,
    'audio/ogg':  process_voice_messages,
    'audio/mpeg': process_voice_messages,
    'audio/mp4':  process_voice_messages,
    'audio/wav':  process_voice_messages,
}


async def process_doc_messages(doc_msgs: list[LocalRawMessages], ctx: AppContext = None) -> list[LocalRawMessages]:
    """Функция сохранения документа из базы данных."""

    for i, msg in enumerate(doc_msgs):

        if ctx and msg.file_mime_type in MIME_TO_HANDLER:
            function = MIME_TO_HANDLER[msg.file_mime_type]
            doc_msgs[i] = (await function(ctx, [msg]))[0]
            continue

        if msg.file_name:
            filename = msg.file_name
        else:
            ext = mimetypes.guess_extension(msg.file_mime_type) or '.bin'
            filename = f'Файл_от_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}{ext}'

        try:
            logger.info(f"Обрабатываем сообщение с документом {msg.id}...")
            doc_path = Path(msg.file_path)
            safe_name = re.sub(r'[^\w.]', '_', filename)
            new_path = doc_path.parent / safe_name
            doc_path.rename(new_path)
            msg.file_path = str(new_path)
            msg.msg_status = "done"

        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            msg.msg_status = "error_save"

    return doc_msgs