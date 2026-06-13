import asyncio

from src.agents.obsidian_agent import start_analyze_agent
from src.agents.graph import graph_builder
from src.logger import setup_logger
from src.msg_assembler.assembler import prepare_msgs
from src.msg_collector.telethon_collector import collect_and_save
from src.agents.summary_graph import summary_graph_builder
from src.agents.summary_agent import run_weekly_summary


setup_logger()


async def handle_msgs():
    await collect_and_save()
    await prepare_msgs()


async def agentic_cycle():
    agent_graph = graph_builder()
    await start_analyze_agent(agent_graph)

async def summary_cycle():
    summary_graph = summary_graph_builder()
    await run_weekly_summary(summary_graph)

async def main():
    await handle_msgs()
    await agentic_cycle()
    await summary_cycle()

if __name__ == '__main__':
    asyncio.run(main())

