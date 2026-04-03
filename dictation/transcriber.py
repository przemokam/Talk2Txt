"""Speech-to-text transcription using Parakeet TDT via MLX."""

import gc
import os
import numpy as np

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


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
        """Transcribe audio numpy array directly — no ffmpeg needed."""
        import mlx.core as mx
        from parakeet_mlx.audio import get_logmel

        self._ensure_model()

        # Convert numpy float32 → mlx array (same as load_audio output)
        audio_mx = mx.array(audio).astype(mx.float32)

        # Resample if needed (model expects 16kHz)
        model_sr = self._model.preprocessor_config.sample_rate
        if sample_rate != model_sr:
            import soxr
            audio_resampled = soxr.resample(audio, sample_rate, model_sr)
            audio_mx = mx.array(audio_resampled).astype(mx.float32)
            del audio_resampled

        mel = get_logmel(audio_mx, self._model.preprocessor_config)
        del audio_mx
        result = self._model.generate(mel)[0]
        text = result.text.strip()
        del mel, result

        # Free MLX Metal memory cache and run garbage collection
        mx.metal.clear_cache()
        gc.collect()

        return text
