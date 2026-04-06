from pathlib import Path
from datetime import datetime
from typing import Dict

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent

MONTH_MAPS = {
    '01': 'январь', '02': 'февраль', '03': 'март',
    '04': 'апрель', '05': 'май', '06': 'июнь',
    '07': 'июль', '08': 'август', '09': 'сентябрь',
    '10': 'октябрь', '11': 'ноябрь', '12': 'декабрь',
}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Telegram
    BOT_TOKEN: str
    COLLECTOR_API_KEY: str
    COLLECTOR_URL: str
    FAMILY_CHAT_IDS: Dict[int, str]
    FORUM_CHAT_ID: int
    MSG_TYPES: list[str] = ["voice", "text", "photo", 'document', 'video']
    MSG_SESSION_THRESHOLD: dict[str, int] = {"notes": 5, "diary": 10}
    
    # Obsidian
    OBSIDIAN_VAULT_PATH: Path 

    # llama-server
    LLAMA_SERVER_URL: str = "http://localhost:8080"
    LLAMA_SERVER_PORT: int = 8080

    # STT_Модели
    STT_MODEL: str = 'nemo-conformer-tdt' # gigaam-v3-e2e-rnnt
    STT_MODEL_PATH: str = f"{BASE_DIR}/llm_models/stt_models/parakeet-tdt-0.6b-v3-int8/"
    # VISION_MMPROJ_FILE: str = "vision/mmproj-Qwen3.5-4B-BF16.gguf"

    # Режим подключения
    CONNECTION_TYPE: str = "offline"

    # --- вычисляемые пути ---
    def get_media_path(self, msg_type: str) -> Path:
        now = datetime.now()
        year = str(now.year)
        month = now.strftime("%m")
        return self.OBSIDIAN_VAULT_PATH / 'files' / msg_type / year / f"{MONTH_MAPS[month]}"

    @property
    def models(self) -> dict:
        return {
            "agent": {
                "file": "GigaChat3.1-10B-A1.8B-q6_K.gguf",
                "args": ["--reasoning", "off", "--ctx-size", "32768"],
                "max_tokens": 2048,
            },
            "vision": {
                "file": "google_gemma-4-E4B-it-Q5_K_M.gguf", # Qwen3.5-4B-Q4_K_M.gguf | google_gemma-4-E4B-it-Q5_K_M
                "args": [
                    "--mmproj", str(self.llm_model_path / "mmproj-google_gemma-4-E4B-it-f16.gguf"), # mmproj-google_gemma-4-E4B-it-f16 | mmproj-Qwen3.5-4B-BF16.gguf
                    "--ctx-size", "8192",
                    # "--reasoning", "off", # Это параметры для Qwen3.5
                    # "--image-min-tokens", "1024",
                ],
                "max_tokens": 1024,
            },
        }

    @property
    def llm_model_path(self) -> Path:
        return BASE_DIR / "llm_models"

settings = Settings()
