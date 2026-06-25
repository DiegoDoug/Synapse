"""Kokoro TTS client (integration layer).

Thin wrapper over a ``kokoro.KPipeline``. The pipeline is imported and built
lazily on first synthesis and cached, so the app boots without Kokoro installed.
``synthesize`` returns a complete WAV byte string (assembled with the stdlib
``wave`` module from the pipeline's float32 chunks); ``synthesize_chunks`` yields
per-segment WAV blobs for streaming. Failures normalize to ``KokoroError``.
"""

from __future__ import annotations

import io
import wave
from collections.abc import Iterator

from backend.integrations.base import Integration


class KokoroError(RuntimeError):
    """Text-to-speech failed (not installed, pipeline load, or synthesis)."""


class KokoroClient(Integration):
    """Local text-to-speech via Kokoro, scoped to one voice + sample rate."""

    def __init__(
        self,
        *,
        voice: str = "af_heart",
        sample_rate: int = 24000,
        lang_code: str = "a",
    ) -> None:
        self._voice = voice
        self._sample_rate = sample_rate
        self._lang_code = lang_code
        self._pipeline = None  # lazily loaded

    @property
    def provider(self) -> str:
        return "kokoro"

    @property
    def voice(self) -> str:
        return self._voice

    def available(self) -> bool:
        """True when Kokoro is importable (pipeline not built yet)."""
        try:
            import kokoro  # noqa: F401
        except ImportError:
            return False
        return True

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        """Return a single WAV byte string for ``text``."""
        samples = self._generate(text, voice=voice)
        return self._to_wav(samples)

    def synthesize_chunks(
        self, text: str, *, voice: str | None = None
    ) -> Iterator[bytes]:
        """Yield one WAV blob per synthesized segment (for streaming)."""
        pipeline = self._ensure_pipeline()
        chosen = voice or self._voice
        try:
            for _gs, _ps, audio in pipeline(text, voice=chosen):
                yield self._to_wav(self._to_int16(audio))
        except Exception as exc:  # noqa: BLE001 — normalize synthesis failures
            raise KokoroError(f"Speech synthesis failed: {exc}") from exc

    # --- Internals ---------------------------------------------------------

    def _generate(self, text: str, *, voice: str | None):
        pipeline = self._ensure_pipeline()
        chosen = voice or self._voice
        try:
            import numpy as np

            parts = [audio for _gs, _ps, audio in pipeline(text, voice=chosen)]
            if not parts:
                return b""
            combined = np.concatenate(parts)
            return self._to_int16(combined)
        except KokoroError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize synthesis failures
            raise KokoroError(f"Speech synthesis failed: {exc}") from exc

    def _to_int16(self, audio) -> bytes:
        """Convert a float32 [-1, 1] array to little-endian int16 PCM bytes."""
        import numpy as np

        array = np.asarray(audio, dtype="float32")
        clipped = np.clip(array, -1.0, 1.0)
        return (clipped * 32767.0).astype("<i2").tobytes()

    def _to_wav(self, pcm: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # int16
            wav.setframerate(self._sample_rate)
            wav.writeframes(pcm)
        return buffer.getvalue()

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from kokoro import KPipeline
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise KokoroError(
                "Text-to-speech is unavailable: the 'kokoro' package is not "
                "installed."
            ) from exc
        try:
            self._pipeline = KPipeline(lang_code=self._lang_code)
        except Exception as exc:  # noqa: BLE001 — pipeline / model load failure
            raise KokoroError(f"Could not load Kokoro pipeline: {exc}") from exc
        return self._pipeline
