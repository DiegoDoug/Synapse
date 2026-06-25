"""Voice routes — local speech-to-text and text-to-speech.

Endpoints (under /api/v1):
- GET  /voice/config       capabilities + current voice settings (for the UI)
- POST /voice/transcribe   transcribe an uploaded audio clip → text
- POST /voice/synthesize   synthesize text → a WAV audio stream
- WS   /voice/ws           wake-word mode: stream PCM, receive detection +
                           transcript events

Voice only converts audio ↔ text; the transcript is fed back into the existing
AI chat by the client, so no AI/tool/confirmation logic lives here. STT/TTS and
wake word are optional: when the local model packages aren't installed the REST
endpoints return 503, ``/voice/config`` reports them unavailable, and the
WebSocket sends an ``unavailable`` event and closes.
"""

import io

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import (
    get_stt_service,
    get_tts_service,
    get_wakeword_service,
)
from backend.config import Settings, get_settings
from backend.integrations.voice.kokoro import KokoroError
from backend.integrations.voice.whisper import WhisperError
from backend.schemas.voice import SynthesizeRequest, TranscriptResult, VoiceConfig
from backend.services.stt_service import STTService
from backend.services.tts_service import TTSService
from backend.services.voice_session import VoiceSession, VoiceSessionConfig
from backend.services.wakeword_service import WakeWordService

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/config", response_model=VoiceConfig)
def voice_config(
    settings: Settings = Depends(get_settings),
    stt: STTService = Depends(get_stt_service),
    tts: TTSService = Depends(get_tts_service),
    wake_word: WakeWordService = Depends(get_wakeword_service),
) -> VoiceConfig:
    return VoiceConfig(
        stt_available=stt.available,
        tts_available=tts.available,
        wake_word_available=wake_word.available,
        whisper_model=settings.whisper_model,
        tts_voice=settings.tts_voice,
        wake_word_model=settings.wake_word_model,
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


@router.websocket("/ws")
async def voice_ws(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
    wake_word: WakeWordService = Depends(get_wakeword_service),
    stt: STTService = Depends(get_stt_service),
) -> None:
    """Wake-word stream: client sends 16 kHz int16 PCM frames (binary); server
    replies with JSON events (``ready`` / ``wake_word_detected`` / ``listening``
    / ``transcript`` / ``error``). Closes after an ``unavailable`` event when the
    wake-word or STT model isn't installed."""
    await websocket.accept()
    if not (wake_word.available and stt.available):
        await websocket.send_json(
            {
                "event": "unavailable",
                "detail": "Wake-word mode needs the voice extras installed.",
            }
        )
        await websocket.close()
        return

    session = VoiceSession(
        wake_word,
        stt,
        config=VoiceSessionConfig(
            sample_rate=settings.voice_sample_rate,
            silence_ms=settings.voice_silence_ms,
            max_utterance_ms=settings.voice_max_utterance_ms,
            silence_rms=settings.voice_silence_rms,
        ),
    )
    await websocket.send_json({"event": "ready"})
    try:
        while True:
            frame = await websocket.receive_bytes()
            # Inference is blocking; run it off the event loop.
            for event in await run_in_threadpool(session.push, frame):
                await websocket.send_json(event)
    except WebSocketDisconnect:
        return
