"""Audio recorder using sounddevice."""

import numpy as np
import sounddevice as sd
import threading


class Recorder:
    """Records audio from the microphone. Thread-safe start/stop."""

    def __init__(self, sample_rate: int = 16000, device: int | None = None):
        self.sample_rate = sample_rate
        self.device = device
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.is_recording = False

    def _callback(self, indata, frames, time_info, status):
        self._chunks.append(indata.copy())

    def start(self):
        with self._lock:
            if self.is_recording:
                return
            self._chunks = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device,
                callback=self._callback,
            )
            self._stream.start()
            self.is_recording = True

    def stop(self) -> np.ndarray | None:
        with self._lock:
            if not self.is_recording or self._stream is None:
                return None
            self._stream.stop()
            self._stream.close()
            self._stream = None
            self.is_recording = False
            if not self._chunks:
                return None
            audio = np.concatenate(self._chunks, axis=0).flatten()
            self._chunks = []  # free chunk references immediately
            return audio
