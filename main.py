import asyncio

from src.logger import setup_logger
from src.msg_assembler.assembler import prepare_msgs
from src.msg_collector.telethon_collector import collect_and_save

setup_logger()


async def main():
    await collect_and_save()
    await prepare_msgs()

if __name__ == '__main__':
    asyncio.run(main())

