"""Wake-word service — business logic over the openWakeWord client.

Decides whether a streamed audio frame triggers the wake word by comparing the
client's score against a threshold. The detection-to-recording flow it feeds
lives in ``VoiceSession``; this service only answers "did the wake word fire?".
"""

from __future__ import annotations

from backend.integrations.voice.wakeword import OpenWakeWordClient


class WakeWordService:
    """Detect a wake word in streamed 16 kHz int16 PCM frames."""

    def __init__(self, client: OpenWakeWordClient, *, threshold: float = 0.5) -> None:
        self._client = client
        self._threshold = threshold

    @property
    def available(self) -> bool:
        return self._client.available()

    def detect(self, frame: bytes) -> bool:
        """Return True when ``frame`` pushes the wake-word score over threshold.

        Raises ``WakeWordError`` (from the client) on an inference failure.
        """
        if not frame:
            return False
        return self._client.score(frame) >= self._threshold
