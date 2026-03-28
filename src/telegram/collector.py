import asyncio
import pprint
from datetime import datetime

import httpx
from src.config import settings


TG_API = f"https://api.telegram.org/bot{settings.BOT_TOKEN}"
MSG_TYPES = ['voice', 'text', 'photo']

THREAD_MAPS = {
    2: "diary",
    4: "calendar",
    6: "notes",
    8: "task",
}


async def fetch_updates(offset: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{TG_API}/getUpdates",
            params={"offset": offset + 1, "limit": 100, "timeout": 0},
        )
        data = r.json()
        if not data["ok"]:
            raise RuntimeError(f"Telegram API error: {data}")
        return data["result"]


async def collect_and_print(msg: int = 0):
    """Забрать все накопленные обновления и вывести на печать."""
    updates = await fetch_updates(offset=msg)

    for update in updates:
        msg = update['message']

        msg_type = [tp for tp in MSG_TYPES if tp in msg]
        if not msg_type:
            print(f'В сообщении нет нужных типов из {MSG_TYPES}')
            continue

        if 'text' in msg_type:
            final_dict = await handle_text_messages(msg)
            print(f'message is TEXT. and it contains\n{final_dict}')


        # print(f'message type is: {msg_type[0]} From {msg['from']['first_name']}')


        # pprint.pprint(update)


        # if "message" not in update:
        #     continue

        # msg = update["message"]
        # thread_id = msg.get("message_thread_id")
        # author = msg.get("from", {}).get("first_name", "Unknown")
        # text = msg.get("text") or "(не текст)"

        # print(f"thread={thread_id} | {author}: {text}")


async def handle_text_messages(message: dict) -> dict:
    author_id = message['from']['id']
    author_username = message['from']['username']
    author_name = settings.FAMILY_CHAT_IDS.get(author_id, '')
    if not author_name:
        print('Необходимо проверить env файл и заполнить правильно FAMILY_CHAT_IDS')
    message_thread = THREAD_MAPS.get(message['message_thread_id'], '')
    if not message_thread:
        print('Необходимо проверить THREAD_MAPS на соответствие возвращаемому от телеграм')
    date = datetime.fromtimestamp(message['date'], tz=None)
    text = message['text']
    return {
        "author_id": author_id,
        "author_username": author_username,
        "author_name": author_name,
        "message_thread": message_thread,
        "date": date,
        "text": text
    }



if __name__ == "__main__":
    asyncio.run(collect_and_print())
