from pathlib import Path
from datetime import datetime
import re
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

    TG_API_ID: int
    TG_API_HASH: str

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
    STT_MODEL: str = "nemo-conformer-tdt"
    STT_MODEL_PATH: str = f"{BASE_DIR}/llm_models/stt_models/parakeet-tdt-0.6b-v3-int8/"

    # Режим подключения
    CONNECTION_TYPE: str = "offline"
    AGENT_ATTEMPTS: int = 2

    # --- вычисляемые пути ---
    def get_media_path(self, msg_type: str) -> Path:
        now = datetime.now()
        year = str(now.year)
        month = now.strftime("%m")
        return self.OBSIDIAN_VAULT_PATH / 'files' / msg_type / year / f"{MONTH_MAPS[month]}"
    
    def get_note_path(self, thread: str, created_at: str, title: str | None = None) -> Path:
        date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        month = date.strftime("%m")
        year = date.strftime("%Y")
        
        if title:
            raw_title = re.sub(r'[^\w\s]', '', title)
            ready_title = raw_title.strip().replace(' ', '_')[:50]
            return self.OBSIDIAN_VAULT_PATH / thread / year / f"{month}-{MONTH_MAPS[month]}" / f"{ready_title}.md"
        
        if thread == "calendar":
            return self.OBSIDIAN_VAULT_PATH / thread / year / f"{month}-{MONTH_MAPS[month]}.md"
        
        if thread == "task":
            week = date.isocalendar()[1]
            return self.OBSIDIAN_VAULT_PATH / thread / year / f"{month}-{MONTH_MAPS[month]}" / f"неделя-{week}.md"

        raise ValueError(f"Неизвестный тред: {thread}")

    @property
    def models(self) -> dict:
        return {
            "GigaChat": {
                "file": "GigaChat3.1-10B-A1.8B-q6_K.gguf",
                "args": ["--reasoning", "off", "--ctx-size", "32768"],
                "max_tokens": 4096,
            },
            "Gemma-4": {
                "file": "supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf",
                "args": ["--reasoning", "off", "--ctx-size", "50000"],
                "max_tokens": 4096,
            },
            "Qwen3.6": {
                "file": "Qwen3.6-35B-A3B-UD-IQ3_S.gguf",
                "args": ["--reasoning", "off", "--ctx-size", "50000"],
                "max_tokens": 8000,
            },
            "vision": {
                "file": "Qwen3-VL-4B-Instruct-Q6_K.gguf",
                "args": [
                    "--mmproj", str(self.llm_model_path / "mmproj-Qwen3-VL-4B-Instruct-F16.gguf"),
                    "--ctx-size", "8192",
                ],
                "max_tokens": 1024,
            },
        }

    @property
    def llm_model_path(self) -> Path:
        return BASE_DIR / "llm_models"

settings = Settings()
