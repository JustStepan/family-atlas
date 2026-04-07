import asyncio

from src.agents.text import test_agent
from src.msg_assembler.assembler import prepare_msgs
from src.msg_collector.collect_msg import save_msgs


async def main():

    await save_msgs()
    await asyncio.sleep(2)
    results = await test_agent()
    print('START AGENT CYCLE')
    for r in results:
        print("TAGS:", r.tags, "SUMMARY", r.summary, sep='\n\n')
    print('END AGENT CYCLE')

if __name__ == '__main__':

    messages_collected = asyncio.run(main())
    # print(messages_collected)
    # if messages_collected:
    # print(asyncio.run(prepare_msgs()))