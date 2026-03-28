from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

async def summarize(llm: ChatOpenAI, text: str) -> str:
    """llm принимает снаружи — не создаёт сам."""
    message = HumanMessage(content=f'Ты дружелюбный помощник. Ответь по возможности на запрос пользователя: {text}')
    resp = await llm.ainvoke([message])
    return resp.content