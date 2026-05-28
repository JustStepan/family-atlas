"""
Скрипт автоматической загрузки моделей для Family Atlas.

Скачивает автоматически:
    - STT модель Parakeet TDT 0.6B v3 (onnx-asr, int8, ~600 MB)
    - STT модель Gigaam e2e-rnnt (onnx-asr, ~900 MB)
    - Embedding модель LaBSE-ru-turbo (~500 MB)

GGUF модели (агент, vision, нормализатор STT) скачиваются вручную.
Инструкция — в README.md раздел "Загрузка моделей".

Запуск:
    uv run src/helpers/download_models.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
EMB_DIR = BASE_DIR / "llm_models" / "embeddings"


def download_parakeet() -> bool:
    """Скачивает Parakeet TDT 0.6B v3 (ONNX int8) и сохраняет локально."""
    print("\n[1/3] Скачиваем Parakeet TDT 0.6B v3...")
    try:
        import onnx_asr
        onnx_asr.load_model(
            "nemo-parakeet-tdt-0.6b-v3",
            str(BASE_DIR / "llm_models" / "stt_models" / "parakeet-tdt-0.6b-v3-int8"),
            quantization="int8",
            providers=["CPUExecutionProvider"],
        )
        print(f"    ✓ STT модель сохранена: {str(BASE_DIR / "llm_models" / "stt_models" / "parakeet-tdt-0.6b-v3-int8")}")
        return True
    except Exception as e:
        print(f"    ✗ Ошибка: {e}")
        return False
    

def download_gigaam() -> bool:
    """Скачивает gigaam-v3-e2e-rnnt и сохраняет локально."""
    print("\n[2/3] Скачиваем gigaam-v3-e2e-rnnt...")
    try:
        import onnx_asr
        onnx_asr.load_model(
            "gigaam-v3-e2e-rnnt",
            str(BASE_DIR / "llm_models" / "stt_models" / "gigaam-v3-e2e-rnnt"),
            providers=["CPUExecutionProvider"],
        )
        print(f"    ✓ STT модель сохранена: {str(BASE_DIR / "llm_models" / "stt_models" / "gigaam-v3-e2e-rnnt")}")
        return True
    except Exception as e:
        print(f"    ✗ Ошибка: {e}")
        return False


def download_embeddings() -> bool:
    """Скачивает LaBSE-ru-turbo с HuggingFace."""
    print("\n[3/3] Скачиваем embedding модель LaBSE-ru-turbo...")
    EMB_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("sergeyzh/LaBSE-ru-turbo")
        model.save(str(EMB_DIR / "LaBSE-ru-turbo"))
        print(f"    ✓ Embedding модель сохранена: {EMB_DIR / "LaBSE-ru-turbo"}")
        return True
    except Exception as e:
        print(f"    ✗ Ошибка загрузки embedding: {e}")
        return False


if __name__ == "__main__":
    print("Family Atlas — загрузка моделей")
    print("=" * 50)

    results = [download_parakeet(), download_gigaam(), download_embeddings()]

    if all(results):
        print("\n✓ Готово. Не забудьте скачать GGUF файлы вручную (см. README.md).\n")
    else:
        print("\n✗ Часть моделей не загрузилась. Проверьте ошибки выше.\n")
        sys.exit(1)