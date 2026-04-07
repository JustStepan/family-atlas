from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select

from src.prompts.texts import TEXTS_SYSTEM_MSG
from src.agents.schemas import TextSummarizerOutput
from src.infrastructure.context import AppContext
from src.database.models import AssembledMessages
from src.database.engine import get_db


async def get_assembled_msgs():
    async with get_db() as session:
        query = await session.execute(
            select(AssembledMessages)
            .where(AssembledMessages.session_status == 'ready')
        )
        ready_sessions = query.scalars().all()
        if ready_sessions: 
            print(f'получено {len(ready_sessions)} сообщений')
        return ready_sessions


async def get_texts(messages):
    """llm принимает снаружи — не создаёт сам."""

    async with AppContext(verbose=False) as ctx:
        await ctx.use_model("agent")

        if not messages:
            return {"message": "ообщений для текстовой обработки нет"}

        all_msgs = []        
        for num, msg in enumerate(messages):
            print(f'WORK ON {num} MESSAGE')
            system_msg = SystemMessage(content=TEXTS_SYSTEM_MSG)
            hum_msg = HumanMessage(content=f'Суммаризуй представленный текст\n{msg.content}')
            structured_llm = ctx.llm.with_structured_output(TextSummarizerOutput)
            response = await structured_llm.ainvoke([system_msg, hum_msg])
            all_msgs.append(response)
            
        return all_msgs


async def test_agent():
    messages = await get_assembled_msgs()
    agent_response = await get_texts(messages)
    return agent_response