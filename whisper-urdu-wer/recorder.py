"""Record a short microphone clip to a 16 kHz mono WAV file.

Press Enter to start, Enter again to stop. On macOS the first run asks
for microphone permission for Terminal; allow it, then run again.
"""
from __future__ import annotations

import threading
import wave
from pathlib import Path
from typing import List

import numpy as np

SAMPLE_RATE = 16_000  # Whisper works at 16 kHz, so record at that rate.
SILENCE_PEAK = 0.01  # peak amplitude below this means the mic gave silence


def record_clip(path: Path) -> float:
    """Record until Enter is pressed; return duration in seconds."""
    import sounddevice as sd  # imported here so tests do not need audio drivers

    chunks: List[np.ndarray] = []
    lock = threading.Lock()

    def callback(indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        with lock:
            chunks.append(indata.copy())

    input("    Press Enter to START recording...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
        input("    Recording. Read the text, then press Enter to STOP.")

    with lock:
        audio = np.concatenate(chunks).ravel() if chunks else np.zeros(0, dtype=np.float32)

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak < SILENCE_PEAK:
        raise RuntimeError(
            "The recording is silent. Allow microphone access for Terminal in "
            "System Settings > Privacy & Security > Microphone, then run again."
        )

    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())
    return len(pcm) / SAMPLE_RATE
