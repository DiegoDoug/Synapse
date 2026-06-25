"""Stage 4.7 (Major Feature 2) tests — wake-word service, session, WebSocket.

openWakeWord and faster-whisper are faked in-memory, so the tests cover the
detection threshold, the listening→recording→transcript state machine (with the
energy VAD), the WebSocket protocol, and graceful degradation when the wake-word
or STT model is absent.
"""

import struct

import pytest
from backend.api.dependencies import get_stt_service, get_wakeword_service
from backend.integrations.voice.wakeword import OpenWakeWordClient, WakeWordError
from backend.main import app
from backend.schemas.voice import TranscriptResult
from backend.services.voice_session import VoiceSession, VoiceSessionConfig
from backend.services.wakeword_service import WakeWordService
from fastapi.testclient import TestClient


def _frame(amplitude: int, samples: int = 160) -> bytes:
    """A mono int16 PCM frame at a constant amplitude (loud = speech)."""
    return struct.pack(f"<{samples}h", *([amplitude] * samples))


LOUD = _frame(20000)
QUIET = _frame(0)


# --- Fakes -------------------------------------------------------------------


class FakeWakeClient:
    """Scores high only for frames tagged by a marker amplitude."""

    def __init__(self, *, available=True):
        self._available = available

    def available(self):
        return self._available

    def score(self, frame):
        # Treat a max-amplitude (32767) marker sample as the wake word.
        return 0.9 if b"\xff\x7f" in frame else 0.0


class FakeSTT:
    def __init__(self, *, available=True, text="hello there"):
        self.available = available
        self._text = text
        self.calls = 0

    def transcribe_pcm(self, pcm, *, sample_rate=16000, language=None):
        self.calls += 1
        return TranscriptResult(text=self._text)


def _marker_frame() -> bytes:
    # Contains a 32767 sample (b"\xff\x7f") so FakeWakeClient fires.
    return struct.pack("<4h", 32767, 20000, 20000, 20000)


# --- WakeWordService ---------------------------------------------------------


def test_wakeword_service_threshold():
    service = WakeWordService(FakeWakeClient(), threshold=0.5)
    assert service.detect(_marker_frame()) is True
    assert service.detect(LOUD) is False
    assert service.detect(b"") is False


def test_wakeword_client_degrades_without_package():
    try:
        import openwakeword  # noqa: F401

        pytest.skip("openwakeword installed; degradation path not exercised")
    except ImportError:
        pass
    client = OpenWakeWordClient()
    assert client.available() is False
    with pytest.raises(WakeWordError):
        client.score(LOUD)


# --- VoiceSession state machine ----------------------------------------------


def _session(stt=None) -> VoiceSession:
    return VoiceSession(
        WakeWordService(FakeWakeClient(), threshold=0.5),
        stt or FakeSTT(),
        # Small silence window so a couple of quiet frames end the utterance.
        config=VoiceSessionConfig(silence_ms=20, max_utterance_ms=5000),
    )


def test_session_ignores_audio_until_wake_word():
    session = _session()
    assert session.push(LOUD) == []  # listening, no wake word
    assert session.recording is False


def test_session_detects_then_transcribes_on_silence():
    stt = FakeSTT(text="add a task")
    session = _session(stt)

    assert session.push(_marker_frame()) == [{"event": "wake_word_detected"}]
    assert session.recording is True

    session.push(LOUD)  # speech buffered
    events: list[dict] = []
    for _ in range(50):  # trailing silence ends the utterance
        events = session.push(QUIET)
        if events:
            break
    kinds = [e["event"] for e in events]
    assert "transcript" in kinds and "listening" in kinds
    transcript = next(e for e in events if e["event"] == "transcript")
    assert transcript["text"] == "add a task"
    assert stt.calls == 1
    assert session.recording is False


def test_session_silent_utterance_is_dropped():
    stt = FakeSTT()
    session = _session(stt)
    session.push(_marker_frame())  # wake
    events: list[dict] = []
    for _ in range(50):
        events = session.push(QUIET)
        if events:
            break
    # All-silence buffer → just back to listening, no transcription.
    assert events == [{"event": "listening"}]
    assert stt.calls == 0


def test_session_surfaces_wake_word_errors():
    class Boom:
        def available(self):
            return True

        def score(self, frame):
            raise WakeWordError("inference boom")

    session = VoiceSession(
        WakeWordService(Boom(), threshold=0.5), FakeSTT()
    )
    assert session.push(LOUD) == [{"event": "error", "detail": "inference boom"}]


# --- WebSocket ---------------------------------------------------------------


def _ws_client(*, wake, stt) -> TestClient:
    app.dependency_overrides[get_wakeword_service] = lambda: wake
    app.dependency_overrides[get_stt_service] = lambda: stt
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_config_reports_wake_word_availability():
    app.dependency_overrides[get_wakeword_service] = lambda: WakeWordService(
        FakeWakeClient(available=True)
    )
    body = TestClient(app).get("/api/v1/voice/config").json()
    assert body["wake_word_available"] is True
    assert "wake_word_model" in body


def test_ws_unavailable_when_models_absent():
    client = _ws_client(
        wake=WakeWordService(FakeWakeClient(available=False)),
        stt=FakeSTT(available=False),
    )
    with client.websocket_connect("/api/v1/voice/ws") as ws:
        assert ws.receive_json()["event"] == "unavailable"


def test_ws_full_flow_emits_transcript():
    client = _ws_client(
        wake=WakeWordService(FakeWakeClient(), threshold=0.5),
        stt=FakeSTT(text="what's on my calendar"),
    )
    # 100 ms frames so a few silent frames clear the route's 800 ms threshold
    # (the WebSocket uses the configured silence window, not the test's).
    speech = _frame(20000, samples=1600)
    silence = _frame(0, samples=1600)
    with client.websocket_connect("/api/v1/voice/ws") as ws:
        assert ws.receive_json() == {"event": "ready"}
        ws.send_bytes(_marker_frame())
        assert ws.receive_json() == {"event": "wake_word_detected"}
        ws.send_bytes(speech)
        for _ in range(12):  # ~1.2 s of trailing silence ends the utterance
            ws.send_bytes(silence)
        transcript = None
        for _ in range(5):
            event = ws.receive_json()
            if event["event"] == "transcript":
                transcript = event
                break
        assert transcript is not None
        assert transcript["text"] == "what's on my calendar"
