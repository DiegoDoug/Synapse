"""faster-whisper STT client (integration layer).

Thin wrapper over a ``faster_whisper.WhisperModel``. The model is imported and
loaded lazily on first transcription and cached for the client's lifetime, so
the app boots without faster-whisper installed and only pays the load cost when
voice is actually used. Failures (missing package, bad audio) normalize to
``WhisperError`` so a transcription never crashes the request.
"""

from __future__ import annotations

import io

from backend.integrations.base import Integration


class WhisperError(RuntimeError):
    """Speech-to-text failed (not installed, model load, or decode error)."""


class WhisperClient(Integration):
    """Local speech-to-text via faster-whisper, scoped to one model size."""

    def __init__(
        self,
        *,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None  # lazily loaded

    @property
    def provider(self) -> str:
        return "faster-whisper"

    @property
    def model_size(self) -> str:
        return self._model_size

    def available(self) -> bool:
        """True when faster-whisper is importable (model not loaded yet)."""
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False
        return True

    def transcribe(self, audio: bytes, *, language: str | None = None) -> str:
        """Return the transcript text of an audio clip (any ffmpeg format).

        Loads the model on first use. Raises ``WhisperError`` on any failure.
        """
        model = self._ensure_model()
        try:
            segments, _info = model.transcribe(
                io.BytesIO(audio), language=language
            )
            return "".join(segment.text for segment in segments).strip()
        except Exception as exc:  # noqa: BLE001 — normalize inference failures
            raise WhisperError(f"Transcription failed: {exc}") from exc

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise WhisperError(
                "Speech-to-text is unavailable: the 'faster-whisper' package is "
                "not installed."
            ) from exc
        try:
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        except Exception as exc:  # noqa: BLE001 — model download / load failure
            raise WhisperError(f"Could not load Whisper model: {exc}") from exc
        return self._model
