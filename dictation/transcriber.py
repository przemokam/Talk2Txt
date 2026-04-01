"""Speech-to-text transcription using Parakeet TDT via MLX."""

import os
import tempfile
import time
import numpy as np
import soundfile as sf

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"


class Transcriber:
    """Lazy-loads Parakeet model and transcribes audio."""

    MODEL_NAME = "mlx-community/parakeet-tdt-0.6b-v3"

    def __init__(self):
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from parakeet_mlx import from_pretrained
            self._model = from_pretrained(self.MODEL_NAME)

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        self._ensure_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, sample_rate)
            result = self._model.transcribe(f.name)
        return result.text.strip()
