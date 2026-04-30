"""
Скрипт автоматической загрузки моделей для Family Atlas.

Скачивает автоматически:
    - STT модель GigaAM v3 (onnx-asr, int8, ~600 MB)
    - Embedding модель LaBSE-ru-turbo (~500 MB)

GGUF модели (агент, vision, нормализатор STT) скачиваются вручную.
Инструкция — в README.md раздел "Загрузка моделей".

Запуск:
    uv run src/helpers/download_models.py
"""

import sys
from pathlib import Path

# --- пути ---
BASE_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BASE_DIR / "llm_models"
STT_DIR = MODELS_DIR / "stt_models"
EMB_DIR = MODELS_DIR / "embeddings"

STT_MODEL: str = "nemo-parakeet-tdt-0.6b-v3"
STT_MODEL_PATH: str = str(BASE_DIR / "llm_models/stt_models/parakeet-tdt-0.6b-v3-int8")

EMB_MODEL_ID = "sergeyzh/LaBSE-ru-turbo"
EMB_MODEL_LOCAL = EMB_DIR / "LaBSE-ru-turbo"


def download_stt():
    """Скачивает Parakeet TDT 0.6B v3 (ONNX int8, многоязычный)."""
    print("\n[1/2] Скачиваем Parakeet TDT 0.6B v3...")
    STT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import onnx_asr
        onnx_asr.load_model(
            "nemo-parakeet-tdt-0.6b-v3",
            str(STT_MODEL_LOCAL),
            quantization="int8",
            providers=["CPUExecutionProvider"],
        )
        print(f"    ✓ STT модель сохранена: {STT_MODEL_LOCAL}")
        return True
    except Exception as e:
        print(f"    ✗ Ошибка: {e}")
        return False


def download_embeddings():
    """Скачивает LaBSE-ru-turbo с HuggingFace."""
    print("\n[2/2] Скачиваем embedding модель LaBSE-ru-turbo...")
    EMB_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMB_MODEL_ID)
        model.save(str(EMB_MODEL_LOCAL))
        print(f"    ✓ Embedding модель сохранена: {EMB_MODEL_LOCAL}")
        return True
    except Exception as e:
        print(f"    ✗ Ошибка загрузки embedding: {e}")
        return False


if __name__ == "__main__":
    print("Family Atlas — загрузка моделей")
    print("=" * 50)

    results = []
    results.append(download_stt())
    results.append(download_embeddings())

    if all(results):
        print("\n✓ Готово. Не забудьте скачать GGUF файлы вручную (см. README.md).\n")
    else:
        print("\n✗ Часть моделей не загрузилась. Проверьте ошибки выше.\n")
        sys.exit(1)