"""Voice model clients (integration layer).

Thin wrappers over the local speech models — faster-whisper (STT) and Kokoro
(TTS). They own model loading and inference and nothing else; deciding what to
transcribe/synthesize and how it flows into the AI chat is the service layer's
concern. Both import their (heavy) dependency lazily so the app boots without
the voice extras installed, mirroring the BrowserService / LLM-provider pattern.
"""

from backend.integrations.voice.kokoro import KokoroClient, KokoroError
from backend.integrations.voice.whisper import WhisperClient, WhisperError

__all__ = [
    "KokoroClient",
    "KokoroError",
    "WhisperClient",
    "WhisperError",
]
