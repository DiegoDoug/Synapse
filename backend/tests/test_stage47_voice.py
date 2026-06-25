"""Stage 4.7 (Major Feature 1) tests — local STT/TTS services + voice routes.

The Whisper/Kokoro model clients are faked in-memory (no faster-whisper, Kokoro,
or audio decoding), so the tests cover service behavior, route wiring, and the
graceful-degradation contract: when the optional model packages are absent the
endpoints report unavailable and return 503.
"""

import pytest
from backend.api.dependencies import get_stt_service, get_tts_service
from backend.integrations.voice.kokoro import KokoroClient, KokoroError
from backend.integrations.voice.whisper import WhisperClient, WhisperError
from backend.main import app
from backend.services.stt_service import STTService
from backend.services.tts_service import TTSService
from fastapi.testclient import TestClient

# --- Fake model clients ------------------------------------------------------


class FakeWhisper:
    def __init__(self, *, available=True, text="hello world"):
        self._available = available
        self._text = text

    def available(self):
        return self._available

    def transcribe(self, audio, *, language=None):
        return self._text


class FakeKokoro:
    def __init__(self, *, available=True):
        self._available = available

    def available(self):
        return self._available

    def synthesize(self, text, *, voice=None):
        return b"RIFFfakewav"


# --- Services ----------------------------------------------------------------


def test_stt_service_transcribes_and_rejects_empty():
    service = STTService(FakeWhisper(text="take notes"))
    assert service.available is True
    assert service.transcribe(b"audio").text == "take notes"
    with pytest.raises(WhisperError):
        service.transcribe(b"")


def test_tts_service_synthesizes_and_rejects_empty():
    service = TTSService(FakeKokoro())
    assert service.available is True
    assert service.synthesize("hi").startswith(b"RIFF")
    with pytest.raises(KokoroError):
        service.synthesize("   ")


# --- Real clients degrade without their packages -----------------------------


def test_whisper_client_degrades_without_package():
    try:
        import faster_whisper  # noqa: F401

        pytest.skip("faster-whisper installed; degradation path not exercised")
    except ImportError:
        pass
    client = WhisperClient()
    assert client.available() is False
    with pytest.raises(WhisperError):
        client.transcribe(b"not audio")


def test_kokoro_client_degrades_without_package():
    try:
        import kokoro  # noqa: F401

        pytest.skip("kokoro installed; degradation path not exercised")
    except ImportError:
        pass
    client = KokoroClient()
    assert client.available() is False
    with pytest.raises(KokoroError):
        client.synthesize("hello")


def test_kokoro_to_wav_is_valid_wav_header():
    # The WAV assembly is stdlib-only and must not depend on numpy/Kokoro.
    wav = KokoroClient(sample_rate=24000)._to_wav(b"\x00\x00\x01\x00")
    assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"


# --- Routes ------------------------------------------------------------------


def _client(*, stt, tts) -> TestClient:
    app.dependency_overrides[get_stt_service] = lambda: stt
    app.dependency_overrides[get_tts_service] = lambda: tts
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_voice_config_reports_availability():
    client = _client(
        stt=STTService(FakeWhisper(available=True)),
        tts=TTSService(FakeKokoro(available=False)),
    )
    body = client.get("/api/v1/voice/config").json()
    assert body["stt_available"] is True
    assert body["tts_available"] is False
    assert "whisper_model" in body and "tts_voice" in body


def test_transcribe_returns_text():
    client = _client(
        stt=STTService(FakeWhisper(text="add a task")),
        tts=TTSService(FakeKokoro()),
    )
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json() == {"text": "add a task"}


def test_transcribe_unavailable_returns_503():
    client = _client(
        stt=STTService(FakeWhisper(available=False)),
        tts=TTSService(FakeKokoro()),
    )
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
    )
    assert response.status_code == 503


def test_synthesize_streams_wav():
    client = _client(
        stt=STTService(FakeWhisper()),
        tts=TTSService(FakeKokoro()),
    )
    response = client.post("/api/v1/voice/synthesize", json={"text": "hello"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")


def test_synthesize_unavailable_returns_503():
    client = _client(
        stt=STTService(FakeWhisper()),
        tts=TTSService(FakeKokoro(available=False)),
    )
    response = client.post("/api/v1/voice/synthesize", json={"text": "hello"})
    assert response.status_code == 503
