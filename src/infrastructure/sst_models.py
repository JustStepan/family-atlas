import onnx_asr

from src.config import settings


class STTModels:
    def __init__(self):
        self._parakeet = None
        self._gigaam = None

    @property
    def parakeet(self):
        if self._parakeet is None:
            self._parakeet = onnx_asr.load_model(
                "nemo-conformer-tdt",
                settings.STT_MODEL_PATH / "parakeet-tdt-0.6b-v3-int8",
                quantization="int8",
                providers=["CPUExecutionProvider"],
            )
        return self._parakeet

    @property
    def gigaam(self):
        if self._gigaam is None:
            self._gigaam = onnx_asr.load_model(
                "gigaam-v3-e2e-rnnt",
                settings.STT_MODEL_PATH / "gigaam-v3-e2e-rnnt",
                providers=["CPUExecutionProvider"],
            )
        return self._gigaam

    def unload(self):
        self._parakeet = None
        self._gigaam = None
