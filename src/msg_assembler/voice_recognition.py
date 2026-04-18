import os
import subprocess
from pathlib import Path
from functools import lru_cache

import onnx_asr

from src.config import settings
from src.database.models import LocalRawMessages
from src.logger import logger


# Папка для временных файлов — удаляем после обработки
MEDIA_DIR = settings.get_media_path('voice')
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

@lru_cache(maxsize=1)
def get_sst_model():
    """Загружает модель один раз, кешируется навсегда."""
    return onnx_asr.load_model(
        settings.STT_MODEL,
        settings.STT_MODEL_PATH,
        quantization="int8",        # для Parakeet
        providers=["CPUExecutionProvider"],
        # providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],  # раскомментировать на Intel Mac / Windows / Linux для ускорения
        # providers=["CUDAExecutionProvider", "CPUExecutionProvider"],    # раскомментировать при наличии NVIDIA GPU
    )


def convert_to_wav(audio_path: Path) -> Path:
    """Конвертирует .ogg в .wav через ffmpeg"""
    wav_path = audio_path.with_suffix(".wav")

    result = subprocess.run(
        [
            "ffmpeg", "-y",          # -y перезаписать если существует
            "-i", str(audio_path),
            "-ar", "16000",          # частота дискретизации 16kHz
            "-ac", "1",              # моно канал
            str(wav_path)
        ],
        capture_output=True,         # не выводить в терминал
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode()}")

    return wav_path


def transcribe(wav_path: Path) -> str:
    """Запускает STT модель и возвращает текст."""
    model = get_sst_model()
    # recognize() — синхронный вызов, возвращает строку
    return model.recognize(str(wav_path))


async def process_voice_messages(
    voice_msgs: list[LocalRawMessages]
    ) -> list[LocalRawMessages]:
    """Основная функция обработки голосовых сообщений"""
    for msg in voice_msgs:
        audio_path = None
        wav_path = None

        try:
            logger.info(f"Обрабатываем аудио сообщение {msg.id}...")

            audio_path = Path(msg.file_path)
            # Конвертируем файл
            wav_path = convert_to_wav(audio_path)
            # Транскрибируем
            text = transcribe(wav_path)
            logger.info(f"Транскрипция: {text[:50]}...")

            # Обновляем запись в БД
            msg.content = text
            msg.msg_status = "transcribed"

        except Exception as e:
            logger.error(f"Ошибка STT: {e}")
            msg.msg_status = "error_stt"

            # Удаляем временные файлы в любом случае
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                msg.file_path = None
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)

    return voice_msgs