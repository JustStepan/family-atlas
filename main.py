import asyncio

from src.logger import setup_logger
from src.agents.text import test_agent
from src.msg_assembler.assembler import prepare_msgs
from src.msg_collector.telethon_collector import collect_and_save

setup_logger()


async def main():
    await collect_and_save()
    await prepare_msgs()
    results = await test_agent()
    for r in results:
        print("TAGS:", r.tags)
        print("SUMMARY:", r.summary)
        print('***' * 20)

if __name__ == '__main__':
    asyncio.run(main())

