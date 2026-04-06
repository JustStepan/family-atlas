from datetime import datetime
from pathlib import Path
import mimetypes
import re

from src.msg_assembler.image_describer import process_photo_messages
from src.msg_assembler.voice_recognition import process_voice_messages
from src.config import settings

from src.msg_assembler.telegram_file import download_file
from src.database.models import LocalRawMessages
from src.logger import logger


DOC_DIR = settings.get_media_path('docs')
DOC_DIR.mkdir(parents=True, exist_ok=True)


MIME_TO_HANDLER = {
    # Фото
    'image/jpeg': (process_photo_messages, 'jpeg'),
    'image/png':  (process_photo_messages, 'png'),
    'image/webp': (process_photo_messages, 'webp'),
    'image/gif':  (process_photo_messages, 'gif'),
    # Аудио
    'audio/ogg':  (process_voice_messages, 'ogg'),
    'audio/mpeg': (process_voice_messages, 'mp3'),
    'audio/mp4':  (process_voice_messages, 'm4a'),
    'audio/wav':  (process_voice_messages, 'wav'),
}


def rename_file(old_path: Path, new_name: str) -> Path:
    name = "_".join([n.strip() for n in new_name.split()])
    name = re.sub(r'[^\w]', '_', name)
    new_path = old_path.parent / f'{name}{old_path.suffix}'
    old_path.rename(new_path)
    return new_path


async def process_doc_messages(doc_msgs: list[LocalRawMessages]) -> list[LocalRawMessages]:
    """Функция сохранения документа из базы данных."""

    for i, msg in enumerate(doc_msgs):

        # Если в документах пришел тип данных подлежащий обработке (фото, аудио)
        if msg.msg_type == "document" and msg.file_mime_type in MIME_TO_HANDLER:
            function, ext = MIME_TO_HANDLER[msg.file_mime_type]
            doc_msgs[i] = (await function([msg], ext))[0]
            continue

        # обрабатываем документ как документ
        if msg.file_name:
            filename = msg.file_name
        else:
            ext = mimetypes.guess_extension(msg.file_mime_type) or '.bin'
            filename = f'Файл_от_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}{ext}'

        try:
            logger.info(f"Обрабатываем сообщение с документом {msg.id}...")
            
            extension = Path(filename).suffix.lstrip('.')
            doc_path = await download_file(msg.file_id, DOC_DIR, extension)

            safe_name = re.sub(r'[^\w.]', '_', filename)
            new_path = doc_path.parent / safe_name
            doc_path.rename(new_path)
            msg.file_path = str(new_path)
            msg.msg_status = "done"

        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            msg.msg_status = "error_save"

    return doc_msgs
