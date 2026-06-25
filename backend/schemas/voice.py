"""Voice request/response schemas (DTOs). No business logic.

The typed shapes for the Stage 4.7 voice endpoints: a transcription result, a
synthesis request, and a capability/health view for the settings panel.
"""

from pydantic import BaseModel, Field


class TranscriptResult(BaseModel):
    """Result of transcribing an uploaded audio clip."""

    text: str


class SynthesizeRequest(BaseModel):
    """Body for POST /voice/synthesize."""

    text: str = Field(min_length=1, max_length=4000)
    # Optional voice override; defaults to the configured TTS voice.
    voice: str | None = None


class VoiceConfig(BaseModel):
    """Capabilities + current settings for the voice UI.

    ``stt_available`` / ``tts_available`` reflect whether the (optional) local
    model packages are importable, so the UI can disable controls gracefully.
    """

    stt_available: bool
    tts_available: bool
    whisper_model: str
    tts_voice: str
