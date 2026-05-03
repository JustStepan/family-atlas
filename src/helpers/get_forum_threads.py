"""
Утилита для получения ID топиков Telegram-форума.
Запусти один раз перед настройкой приложения и перенеси
нужные ID в THREAD_MAPS в src/msg_collector/telethon_collector.py

Запуск:
    uv run src/helpers/get_forum_threads.py
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from telethon import TelegramClient
from telethon.tl.types import PeerChannel, MessageService

from src.config import settings


async def get_threads():
    async with TelegramClient(
        "family_atlas",
        settings.TG_API_ID,
        settings.TG_API_HASH,
    ) as client:
        forum = await client.get_entity(
            PeerChannel(channel_id=settings.FORUM_CHAT_ID)
        )
        print(f"\nФорум: {forum.title}")
        print("-" * 40)

        threads = {}
        async for msg in client.iter_messages(forum, limit=500):
            tid = getattr(msg, "reply_to", None)
            if tid and hasattr(tid, "reply_to_top_id"):
                top_id = tid.reply_to_top_id or tid.reply_to_msg_id
            elif tid and hasattr(tid, "reply_to_msg_id"):
                top_id = tid.reply_to_msg_id
            else:
                continue
            if top_id and top_id not in threads:
                threads[top_id] = None

        # получаем названия топиков по их ID
        print(f"{'ID':<6} {'Название'}")
        print("-" * 40)
        for tid in sorted(threads.keys()):
            try:
                msg = await client.get_messages(forum, ids=tid)
                if msg is None:
                    title = "—"
                elif hasattr(msg, "action") and hasattr(msg.action, "title"):
                    title = msg.action.title.lower()
                elif msg.message:
                    title = msg.message[:30]
                else:
                    title = "—"
                print(f"{tid:<6} {title}")
            except Exception as e:
                print(f"{tid:<6} (ошибка: {e})")

        print()
        print("Перенеси нужные ID в THREAD_MAPS в src/msg_collector/telethon_collector.py")


if __name__ == "__main__":
    asyncio.run(get_threads())