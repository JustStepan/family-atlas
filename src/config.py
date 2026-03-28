from pathlib import Path
from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent

MODELS = {
    "gigachat": {
        "file": "GigaChat3.1-10B-A1.8B-q6_K.gguf",
        "args": ["--reasoning", "off", "--ctx-size", "32768"],
        "max_tokens": 2048,
    },
    "vision": {
        "file": "Qwen3.5-4B-Q4_K_M.gguf",
        "args": [
            "--mmproj", str(BASE_DIR / "models" / "mmproj-Qwen3.5-4B-BF16.gguf"),
            "--ctx-size", "8192",
            "--reasoning", "off",
            "--image-min-tokens", "1024",
        ],
        "max_tokens": 1024,
    },
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Telegram
    BOT_TOKEN: str
    OBSIDIAN_VAULT_PATH: str
    FAMILY_CHAT_IDS: Dict[int, str]
    FORUM_CHAT_ID: int
    

    # llama-server
    LLAMA_SERVER_URL: str = "http://localhost:8080"
    LLAMA_SERVER_PORT: int = 8080

    # Модели
    LLM_MODEL_FILE: str = MODELS["gigachat"]["file"]
    VISION_MODEL_FILE: str = MODELS["vision"]["file"]
    # VISION_MMPROJ_FILE: str = "vision/mmproj-Qwen3.5-4B-BF16.gguf"
    

    # Режим подключения
    CONNECTION_TYPE: str = "offline"

    # --- вычисляемые пути ---
    @property
    def llm_model_path(self) -> Path:
        return BASE_DIR / "models"


settings = Settings()