"""Запуск llama-server"""
import asyncio
import httpx

from src.config import settings


BASE_ARGS = [
    "-ngl", "999",
    "--flash-attn", "on",
    "--cache-type-k", "q8_0",
    "--cache-type-v", "q8_0",
    "--port", "8080",
]


class LlamaServer:
    def __init__(self, verbose: bool = False):
        self._verbose = verbose
        self._proc: asyncio.subprocess.Process | None = None

    async def load(self, model_cfg: dict) -> None:
        await self.unload()  # ← всегда чисто выгружаем перед загрузкой

        out = None if self._verbose else asyncio.subprocess.DEVNULL
        self._proc = await asyncio.create_subprocess_exec(
            "llama-server",
            "-m", str(settings.llm_model_path / model_cfg["file"]),
            *BASE_ARGS,
            *model_cfg.get("args", []),
            stdout=out,
            stderr=out,
        )
        await self._wait()

    async def unload(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        await self._proc.wait()
        self._proc = None

    async def _wait(self, timeout: int = 120) -> None:
        async with httpx.AsyncClient() as client:
            for _ in range(timeout):
                try:
                    r = await client.get(f"{settings.LLAMA_SERVER_URL}/health", timeout=2)
                    if r.json().get("status") == "ok":
                        return
                except Exception:
                    pass
                await asyncio.sleep(1)
        raise TimeoutError("Сервер не ответил за 120 секунд")