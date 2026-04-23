import asyncio

from langgraph.graph import StateGraph

from src.agents.graph import graph_builder

from src.agents.schemas import FamilyAtlasState
from src.database.utils import get_assembled_msgs
from src.database.engine import ensure_db_initialized, get_db
from src.infrastructure.context import AppContext


async def start_agent(graph: StateGraph):
    await ensure_db_initialized()
    async with AppContext() as ctx:
        await ctx.use_model("Qwen3.6")
        async with get_db() as session:
            ready_sessions = await get_assembled_msgs(session)
            
            for assembled_msg in ready_sessions:
                state = FamilyAtlasState(
                    session_id=assembled_msg.session_id,
                    message_thread=assembled_msg.message_thread,
                    raw_content=assembled_msg.raw_content,
                    created_at=assembled_msg.created_at,
                    attachments=assembled_msg.attachments or [],
                    author_name=assembled_msg.author_name,
                )
                await graph.ainvoke(
                    state,
                    config={
                        "configurable": {
                            "llm": ctx.llm,
                            "session": session,
                        }
                    }
                )


if __name__ == "__main__":
    agent_graph = graph_builder()
    asyncio.run(start_agent(agent_graph))