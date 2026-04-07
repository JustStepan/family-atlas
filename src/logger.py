import sys
import logging
from pathlib import Path
from loguru import logger

from src.config import BASE_DIR

# ─── Директория для логов ────────────────────────────────────────────────────

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)  # создаём папку, если её нет


# ─── Перехватчик стандартного logging ────────────────────────────────────────
class InterceptHandler(logging.Handler):
    """
    Перенаправляет все логи стандартной библиотеки (logging.*)
    через loguru. Это нужно для uvicorn, sqlalchemy, aiogram и др.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Получаем соответствующий уровень loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # depth=6 — чтобы loguru показал правильный файл/строку,
        # а не внутренности logging.*
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ─── Настройка loguru ─────────────────────────────────────────────────────────
def setup_logger() -> None:
    """
    Инициализирует логер. Вызывать ОДИН РАЗ в main.py.
    Повторный вызов безопасен — старые хендлеры сбрасываются.
    """

    # Удаляем дефолтный хендлер loguru (он выводит всё подряд в stderr)
    logger.remove()

    # Хендлер 1: stdout — только INFO и выше, для живого наблюдения
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{file}</cyan> -> <cyan>{function}:{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level="INFO",
        colorize=True,
    )

    # Хендлер 2: файл — DEBUG и выше, ротация каждую полночь
    logger.add(
        LOGS_DIR / "app_{time:YYYY-MM-DD}.log",  # имя файла = дата старта периода
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {file} -> {function}:{line} | {message}",
        level="DEBUG",
        rotation="00:00",    # новый файл каждую полночь
        retention="7 days",  # удалять файлы старше 7 дней
        compression=None,    # без архивации
        encoding="utf-8",
        enqueue=True,        # потокобезопасная запись (важно для async!)
    )

    # Перехватываем все логи из стандартного logging.*
    # (uvicorn, sqlalchemy, aiogram, httpx и др.)
    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=0,       # пропускаем ВСЕ уровни — loguru сам фильтрует
        force=True,    # переопределяем уже существующие хендлеры
    )