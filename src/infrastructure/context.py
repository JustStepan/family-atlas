from dataclasses import dataclass, field
from langchain_openai import ChatOpenAI
from .llm_server import LlamaServer
from src.config import settings


@dataclass
class AppContext:
    verbose: bool = False
    _server: LlamaServer = field(init=False)
    _llm: ChatOpenAI | None = field(init=False, default=None)

    def __post_init__(self):
        self._server = LlamaServer(verbose=self.verbose)

    async def use_model(self, alias: str) -> None:
        await self._server.load(settings.models[alias])
        self._llm = ChatOpenAI(
            model=alias,
            base_url=f"{settings.LLAMA_SERVER_URL}/v1",
            api_key="dummy",
            temperature=0.1,
            max_tokens=settings.models[alias]["max_tokens"],
        )

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            raise RuntimeError("Модель не загружена. Вызови use_model() сначала.")
        return self._llm

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._server.unload()