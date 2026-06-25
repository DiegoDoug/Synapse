"""Text-to-speech service — business logic over the Kokoro client.

Turns assistant (or arbitrary) text into spoken audio via the ``KokoroClient``
(integration layer). Exposes a one-shot WAV synthesis used by the
``/voice/synthesize`` endpoint to read replies back to the user.
"""

from __future__ import annotations

from backend.integrations.voice.kokoro import KokoroClient, KokoroError


class TTSService:
    """Synthesize speech from text."""

    def __init__(self, client: KokoroClient) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        return self._client.available()

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        """Return a WAV byte string for ``text``. Raises ``KokoroError``."""
        cleaned = text.strip()
        if not cleaned:
            raise KokoroError("No text was provided to synthesize.")
        return self._client.synthesize(cleaned, voice=voice)
