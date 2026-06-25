"""openWakeWord client (integration layer).

Thin wrapper over an ``openwakeword.Model``. The model is imported and loaded
lazily on first frame and cached, so the app boots without openWakeWord
installed. ``score`` feeds a 16 kHz int16 PCM frame to the model and returns the
highest wake-word probability. Failures normalize to ``WakeWordError`` so a bad
frame never tears down the audio stream.
"""

from __future__ import annotations

from backend.integrations.base import Integration


class WakeWordError(RuntimeError):
    """Wake-word detection failed (not installed, model load, or inference)."""


class OpenWakeWordClient(Integration):
    """Local wake-word detection via openWakeWord, scoped to one model."""

    def __init__(self, *, model_name: str = "hey_jarvis") -> None:
        self._model_name = model_name
        self._model = None  # lazily loaded

    @property
    def provider(self) -> str:
        return "openwakeword"

    @property
    def model_name(self) -> str:
        return self._model_name

    def available(self) -> bool:
        """True when openWakeWord is importable (model not loaded yet)."""
        try:
            import openwakeword  # noqa: F401
        except ImportError:
            return False
        return True

    def score(self, frame: bytes) -> float:
        """Return the top wake-word probability for a 16 kHz int16 PCM frame."""
        model = self._ensure_model()
        try:
            import numpy as np

            samples = np.frombuffer(frame, dtype="<i2")
            scores = model.predict(samples)
            return float(max(scores.values())) if scores else 0.0
        except Exception as exc:  # noqa: BLE001 — normalize inference failures
            raise WakeWordError(f"Wake-word inference failed: {exc}") from exc

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        try:
            from openwakeword.model import Model
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise WakeWordError(
                "Wake-word detection is unavailable: the 'openwakeword' package "
                "is not installed."
            ) from exc
        try:
            self._model = Model(wakeword_models=[self._model_name])
        except Exception as exc:  # noqa: BLE001 — model download / load failure
            raise WakeWordError(f"Could not load wake-word model: {exc}") from exc
        return self._model
