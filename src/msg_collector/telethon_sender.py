from telethon import TelegramClient

from src.config import settings
from src.logger import logger


async def send_summary(text: str) -> bool:
    """Шлёт сводку: в тред форума (если задан SUMMARY_THREAD_ID) или в личку family."""
    try:
        async with TelegramClient("family_atlas", settings.TG_API_ID, settings.TG_API_HASH) as client:
            if settings.SUMMARY_THREAD_ID:
                from telethon.tl.types import PeerChannel
                await client.send_message(
                    PeerChannel(channel_id=settings.FORUM_CHAT_ID),
                    text,
                    reply_to=settings.SUMMARY_THREAD_ID,  # пост в нужный тред форума
                )
            else:
                for user_id in settings.FAMILY_CHAT_IDS:  # личка каждому family
                    await client.send_message(user_id, text)
        logger.info("Сводка отправлена в Телеграм")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сводки: {e}")
        return False