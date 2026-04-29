import asyncio

from langgraph.graph import StateGraph

from src.agents.graph import graph_builder

from src.agents.schemas import FamilyAtlasState
from src.database.utils import get_assembled_msgs
from src.database.engine import ensure_db_initialized, get_db
from src.infrastructure.context import AppContext
from src.infrastructure.embeddings import embedding_model


async def start_agent(graph: StateGraph):
    await ensure_db_initialized()
    async with AppContext() as ctx:
        await ctx.use_model("Qwen3.6")
        async with get_db() as session:
            ready_sessions = await get_assembled_msgs(session)

            sessions_data = [
                {
                    "session_id": msg.session_id,
                    "message_thread": msg.message_thread,
                    "raw_content": msg.raw_content,
                    "created_at": msg.created_at,
                    "attachments": msg.attachments or [],
                    "author_name": msg.author_name,
                }
                for msg in ready_sessions
            ]
            
            for assembled_msg in sessions_data:
                state = FamilyAtlasState(**assembled_msg)
                await graph.ainvoke(
                    state,
                    config={
                        "configurable": {
                            "llm": ctx.llm,
                            "session": session,
                            "embedding_model": embedding_model
                        }
                    }
                )


if __name__ == "__main__":
    agent_graph = graph_builder()
    asyncio.run(start_agent(agent_graph))