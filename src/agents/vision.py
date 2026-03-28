from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import base64

async def describe_image(llm: ChatOpenAI, path: str) -> str:
    """llm принимает снаружи — не создаёт сам."""
    data = base64.b64encode(Path(path).read_bytes()).decode('ascii')
    message = HumanMessage(content=[
        {"type": "image_url",
         "image_url": {"url": f"data:image/jpeg;base64,{data}"}},
        {"type": "text", "text": "Опиши что на фотографии."}
    ])
    resp = await llm.ainvoke([message])
    return resp.content