import asyncio
import pprint
from datetime import datetime

import httpx
from src.config import settings
from _local.telegram.logger import logger


TG_API = f"https://api.telegram.org/bot{settings.BOT_TOKEN}"
MSG_TYPES = ["voice", "text", "photo", 'document']

THREAD_MAPS = {
    2: "diary",
    4: "calendar",
    6: "notes",
    8: "task",
}


async def fetch_updates(offset: int) -> list[dict]:
    """Получить обновления от Telegram API начиная с указанного offset."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{TG_API}/getUpdates",
            params={"offset": offset + 1, "limit": 100, "timeout": 0},
        )
        data = r.json()
        if not data["ok"]:
            raise RuntimeError(f"Telegram API error: {data}")
        return data["result"]


async def collect_messages(msg: int = 0):
    """Забрать все накопленные обновления"""
    updates = await fetch_updates(offset=msg)
    logger.info(f"Было собрано {len(updates)} сообщений.")

    for update in updates:
        # Печатаем полный выход из телеги
        # pprint.pprint(update)
        # print()
        msg = update["message"]
        # отсеиваем сообщения которые не содержат message_thread_id 
        # потом можно будет убрать после отладки
        if 'message_thread_id' not in msg:
            continue

        msg_type = [tp for tp in MSG_TYPES if tp in msg]
        if not msg_type:
            logger.error(f"В сообщении нет нужных типов из {MSG_TYPES}")
            continue

        # Печатаем только сообщение messages
        pprint.pprint(msg)
        print()

        final_dict = await handle_message(msg)
        final_dict.update({"msg_type": msg_type[0]})

        # Добавляем содержательные данные (текст, ссылку на фото или документ или аудио...)
        if 'text' in msg_type:
            final_dict.update({"text": msg.get('text')})

        if 'photo' in msg_type:
            final_dict.update({"photo_id": msg.get('photo')[-1]['file_id']})

        if 'voice' in msg_type:
            final_dict.update(
                {
                    "voice_id": msg.get('voice')['file_id'],
                    "voice_mime_type": msg.get('voice')['mime_type'],
                }
            )

        if 'document' in msg_type:
            final_dict.update(
                {
                    "doc_id": msg.get('document')['file_id'],
                    "doc_mime_type": msg.get('document')['mime_type'],
                    "doc_name": msg.get('document')['file_name'],
                }
            )


        # Печатаем то что сами распарсили
        pprint.pprint(final_dict)
        print()


async def handle_message(message: dict) -> dict:
    """Распарсить сообщение и извлечь данные об авторе, теме и метаданных."""
    # Получаем автора
    author_id = message["from"]["id"]
    author_username = message["from"]["username"]
    author_name = settings.FAMILY_CHAT_IDS.get(author_id, "")
    # Обрабатываем ошибку соответствия id автора в env
    if not author_name:
        logger.info(
            "Необходимо проверить env файл и заполнить правильно FAMILY_CHAT_IDS"
        )

    # получаем message_thread - дневник, календарь и проч
    # также делаем проверку на совместимость с THREAD_MAPS
    message_thread = THREAD_MAPS.get(message["message_thread_id"], "")
    if not message_thread:
        logger.info(
            "Необходимо проверить THREAD_MAPS на соответствие возвращаемому от телеграм"
        )

    # Добавляем дату создания.
    create_date = message["date"]
    # datetime.fromtimestamp(message['date'], tz=None)

    result_dict = {
        "author_id": author_id,
        "author_username": author_username,
        "author_name": author_name,
        "message_thread": message_thread,
        "create_date": create_date,
    }

    # Добавляем информацию о пересланном сообщении если есть
    if message.get("forward_origin"):
        result_dict.update(**await handle_forwarded_message_data(message))

    # Добавляем caption если есть
    if caption := message.get('caption'):
        result_dict.update(
            {
                "caption": caption
            }
        )

    return result_dict


async def handle_forwarded_message_data(message: dict) -> dict:
    """Извлечь и обработать данные о пересланном сообщении."""
    forwarded_message_dict = {"forwarded_create_data": message["forward_date"]}
    forward_origin = message["forward_origin"]
    
    # Добавляем дату создания пересланного сообщения
    forwarded_message_dict.update({"forwarded_create_data": message["forward_date"]})

    # Обрабатываем пересланное от пользователя (sender_user)
    if sender_user := forward_origin.get("sender_user"):
        if sender_user["id"] == message["from"]["id"]:
            info_msg = "Автор переслал свое собственное сообщение"
        else:
            if sender_user["id"] in settings.FAMILY_CHAT_IDS:
                info_msg = f"Автор переслал сообщение от {settings.FAMILY_CHAT_IDS[sender_user['id']]}"
            else:
                info_msg = f"Автор переслал сообщение от {sender_user['first_name']} username которого: {sender_user['username']}"
            
        forwarded_message_dict.update(
            {
                "forwarded_msg_info": info_msg
            }
        )
    
    # Обрабатываем пересланное из чата
    if chat := forward_origin.get("chat"):
        username = chat.get('username')
        if username:
            info_msg = f"Автор переслал сообщение из чата с именем '{chat['title']}', username которого: '{chat.get('username')}'"
        else:
            info_msg = f"Автор переслал сообщение из чата с именем '{chat['title']}'"
        forwarded_message_dict.update(
            {
                "forwarded_msg_info": info_msg
            }
        )

    return forwarded_message_dict


if __name__ == "__main__":
    asyncio.run(collect_messages())
