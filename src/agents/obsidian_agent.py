from langgraph.graph import StateGraph

from src.agents.schemas import FamilyAtlasState
from src.agents.writer import write_note
from src.database.utils import get_assembled_msgs, get_analyzed_msgs
from src.database.engine import ensure_db_initialized, get_db
from src.infrastructure.context import AppContext
from src.infrastructure.embeddings import get_embedding_model
from src.config import settings


async def start_analyze_agent(graph: StateGraph):
    await ensure_db_initialized()

    async with get_db() as session:
        ready = await get_assembled_msgs(session)
        analyzed = await get_analyzed_msgs(session)

    if ready:
        sessions_data = [
            {
                "session_id": m.session_id,
                "message_thread": m.message_thread,
                "raw_content": m.raw_content,
                "created_at": m.created_at,
                "attachments": m.attachments or [],
                "author_name": m.author_name,
            }
            for m in ready
        ]
        async with AppContext() as ctx:
            await ctx.use_model(settings.AGENT_MODEL)
            async with get_db() as session:
                for data in sessions_data:
                    await graph.ainvoke(
                        FamilyAtlasState(**data),
                        config={"configurable": {
                            "llm": ctx.llm,
                            "session": session,
                            "embedding_model": get_embedding_model(),
                        }},
                    )
        # Pass 2 — пишем всё что проанализировано (старое + только что)
        async with get_db() as session:
            all_analyzed = await get_analyzed_msgs(session)
            for msg in all_analyzed:
                await write_note(msg, session)

    elif analyzed:
        print(f"Новых сессий нет. Записываем {len(analyzed)} ранее проанализированных файлов")
        async with get_db() as session:
            for msg in analyzed:
                await write_note(msg, session)

    else:
        print("Нечего делать. Выход.")