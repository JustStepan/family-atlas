from functools import cached_property
from pathlib import Path
from datetime import datetime
import re

from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent

MONTH_NAMES: dict[str, str] = {
    "01": "январь",  "02": "февраль", "03": "март",
    "04": "апрель",  "05": "май",     "06": "июнь",
    "07": "июль",    "08": "август",  "09": "сентябрь",
    "10": "октябрь", "11": "ноябрь",  "12": "декабрь",
}


# ---------------------------------------------------------------------------
# Настройки приложения
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # --- Telegram -----------------------------------------------------------

    # --- Данные вашего приложения https://my.telegram.org/apps
    TG_API_ID: int
    TG_API_HASH: str
    FORUM_CHAT_ID: int
    FAMILY_CHAT_IDS: dict[int, str]
    # Максимальный интервал (в минутах) между сообщениями одной сессии
    MSG_SESSION_THRESHOLD: dict[str, int] = {"notes": 5, "diary": 10}

    # --- Google Calendar --------------------------------------------------------
    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_CREDENTIALS_FILE: Path = BASE_DIR / "calendar_credentials.json"
    GOOGLE_TOKEN_FILE: Path = BASE_DIR / "calendar_token.json"

    # --- Obsidian -----------------------------------------------------------
    OBSIDIAN_VAULT_PATH: Path

    # --- llama-server -------------------------------------------------------
    LLAMA_SERVER_URL: str = "http://localhost:8080"
    LLAMA_SERVER_PORT: int = 8080

    # --- STT (onnx-asr) -----------------------------------------------------
    STT_MODEL: str = "nemo-parakeet-tdt-0.6b-v3"
    STT_MODEL_PATH: Path = BASE_DIR / "llm_models" / "stt_models" / "parakeet-tdt-0.6b-v3-int8"

    # --- Embeddings ---------------------------------------------------------
    EMBEDDING_MODEL: str = "sergeyzh/LaBSE-ru-turbo"
    EMBEDDING_MODEL_PATH: Path = BASE_DIR / "llm_models" / "embeddings" / "LaBSE-ru-turbo"

    # --- Агент --------------------------------------------------------------
    # Количество попыток вызова LLM при ошибке structured output
    AGENT_MODEL: str = "Qwen3.6" # Берем из алиасов ниже (в def models(self))
    AGENT_ATTEMPTS: int = 2

    # --- Поиск связанных заметок (find_relatives) ---------------------------
    BM25_THRESHOLD: float = 2.0
    EMBEDDING_THRESHOLD: float = 0.8

    # --- Вычисляемые пути ---------------------------------------------------

    @cached_property
    def llm_model_path(self) -> Path:
        return BASE_DIR / "llm_models"

    @cached_property
    def persons_path(self) -> Path:
        return self.OBSIDIAN_VAULT_PATH / "persons"

    @cached_property
    def models(self) -> dict:
        return {
            "GigaChat": {
                "file": "GigaChat3.1-10B-A1.8B-q6_K.gguf",
                "args": ["--reasoning", "off", "--ctx-size", "16384"],
                "max_tokens": 2048,
            },
            "Gpt-Oss-20b": {
                "file": "gpt-oss-20b-Q8_0.gguf",
                "args": ["--reasoning-budget", "1024", "--ctx-size", "16384"],
                "max_tokens": 4096,
            },
            "Gemma-4": {
                "file": "gemma-4-26B-A4B-Claude-Distill-APEX-I-Compact.gguf",
                "args": ["--reasoning-budget", "1024", "--ctx-size", "16384"],
                "max_tokens": 4096,
            },
            "Qwen3.6": {
                "file": "Qwen3.6-35B-A3B-APEX-I-Compact.gguf",
                "args": ["--reasoning-budget", "1024", "--ctx-size", "16384"],
                "max_tokens": 4096,
            },
            "vision": {
                "file": "Qwen3-VL-4B-Instruct-Q6_K.gguf",
                "args": [
                    "--mmproj", str(self.llm_model_path / "mmproj-Qwen3-VL-4B-Instruct-F16.gguf"),
                    "--ctx-size", "8192",
                    "--reasoning", "off",
                ],
                "max_tokens": 1024,
            },
        }

    def get_media_path(self, msg_type: str) -> Path:
        """Путь для сохранения медиафайлов (фото, голосовые, документы).
        Папка определяется датой запуска процессора."""
        now = datetime.now()
        month = now.strftime("%m")
        return (
            self.OBSIDIAN_VAULT_PATH / "files" / msg_type
            / str(now.year) / MONTH_NAMES[month]
        )

    def get_note_path(self, thread: str, created_at: str, title: str | None = None) -> Path:
        """Детерминированный путь к заметке в Obsidian vault.

        diary/notes/calendar: vault/thread/YYYY/MM-месяц/DD-Заголовок.md
        task:                  vault/thread/YYYY/MM-месяц/WW-неделя.md
        """
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        month_dir = f"{month}-{MONTH_NAMES[month]}"
        base = self.OBSIDIAN_VAULT_PATH / thread / year / month_dir

        if title:
            slug = re.sub(r"[^\w\s]", "", title).strip().replace(" ", "_")[:50]
            return base / f"{day}-{slug}.md"

        if thread == "task":
            week = date.isocalendar()[1]
            return base / f"{week}-неделя.md"

        raise ValueError(f"Неизвестный тред без заголовка: {thread!r}")


settings = Settings()