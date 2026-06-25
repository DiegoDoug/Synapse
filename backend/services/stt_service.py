"""Speech-to-text service — business logic over the Whisper client.

Validates an uploaded clip, delegates transcription to the ``WhisperClient``
(integration layer), and returns a normalized ``TranscriptResult``. The
transcript is meant to be fed into the existing AI chat flow by the caller —
voice adds no new tool or write logic.
"""

from __future__ import annotations

from backend.integrations.voice.whisper import WhisperClient, WhisperError
from backend.schemas.voice import TranscriptResult


class STTService:
    """Transcribe short audio clips to text."""

    def __init__(self, client: WhisperClient) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        return self._client.available()

    def transcribe(
        self, audio: bytes, *, language: str | None = None
    ) -> TranscriptResult:
        """Transcribe ``audio`` to text. Raises ``WhisperError`` on failure."""
        if not audio:
            raise WhisperError("No audio was provided.")
        text = self._client.transcribe(audio, language=language)
        return TranscriptResult(text=text)
