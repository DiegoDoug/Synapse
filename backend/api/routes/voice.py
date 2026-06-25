"""Voice routes — local speech-to-text and text-to-speech.

Endpoints (under /api/v1):
- GET  /voice/config       capabilities + current voice settings (for the UI)
- POST /voice/transcribe   transcribe an uploaded audio clip → text
- POST /voice/synthesize   synthesize text → a WAV audio stream

Voice only converts audio ↔ text; the transcript is fed back into the existing
AI chat by the client, so no AI/tool/confirmation logic lives here. STT/TTS are
optional: when the local model packages aren't installed the endpoints return
503 and ``/voice/config`` reports them unavailable.
"""

import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_stt_service, get_tts_service
from backend.config import Settings, get_settings
from backend.integrations.voice.kokoro import KokoroError
from backend.integrations.voice.whisper import WhisperError
from backend.schemas.voice import SynthesizeRequest, TranscriptResult, VoiceConfig
from backend.services.stt_service import STTService
from backend.services.tts_service import TTSService

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/config", response_model=VoiceConfig)
def voice_config(
    settings: Settings = Depends(get_settings),
    stt: STTService = Depends(get_stt_service),
    tts: TTSService = Depends(get_tts_service),
) -> VoiceConfig:
    return VoiceConfig(
        stt_available=stt.available,
        tts_available=tts.available,
        whisper_model=settings.whisper_model,
        tts_voice=settings.tts_voice,
    )


@router.post("/transcribe", response_model=TranscriptResult)
async def transcribe(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    stt: STTService = Depends(get_stt_service),
) -> TranscriptResult:
    if not stt.available:
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text is unavailable (install the voice extras).",
        )
    audio = await file.read()
    if len(audio) > settings.voice_max_upload_bytes:
        raise HTTPException(status_code=413, detail="Audio clip is too large.")
    if not audio:
        raise HTTPException(status_code=400, detail="No audio was uploaded.")
    try:
        return stt.transcribe(audio)
    except WhisperError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/synthesize")
def synthesize(
    payload: SynthesizeRequest,
    tts: TTSService = Depends(get_tts_service),
) -> StreamingResponse:
    if not tts.available:
        raise HTTPException(
            status_code=503,
            detail="Text-to-speech is unavailable (install the voice extras).",
        )
    try:
        wav = tts.synthesize(payload.text, voice=payload.voice)
    except KokoroError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return StreamingResponse(
        io.BytesIO(wav),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )
