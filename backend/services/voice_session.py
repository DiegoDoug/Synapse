"""Voice wake-word session — the per-connection state machine.

Transport-agnostic so it can be unit-tested without a real WebSocket: feed it
16 kHz int16 PCM frames via ``push`` and it returns the events to send back.

Flow (per ROADMAP Stage 4.7 wake-word mode):

1. **listening** — every frame goes to the wake-word service. On detection it
   emits ``wake_word_detected`` and switches to recording.
2. **recording** — frames are buffered while an energy VAD tracks trailing
   silence. When silence exceeds the threshold (or the utterance hits its cap),
   the buffer is transcribed and emitted as a ``transcript`` event, then the
   session returns to listening.

Detection / transcription failures surface as ``error`` events; the session
keeps running so one bad frame never ends the stream.
"""

from __future__ import annotations

import math
from array import array
from dataclasses import dataclass

from backend.integrations.voice.wakeword import WakeWordError
from backend.integrations.voice.whisper import WhisperError
from backend.services.stt_service import STTService
from backend.services.wakeword_service import WakeWordService

# A frame is int16 mono PCM; 2 bytes per sample.
_BYTES_PER_SAMPLE = 2


@dataclass
class VoiceSessionConfig:
    sample_rate: int = 16000
    silence_ms: int = 800
    max_utterance_ms: int = 15000
    silence_rms: int = 500


class VoiceSession:
    """Drive wake-word detection then utterance capture for one connection."""

    def __init__(
        self,
        wake_word: WakeWordService,
        stt: STTService,
        *,
        config: VoiceSessionConfig | None = None,
    ) -> None:
        self._wake = wake_word
        self._stt = stt
        self._cfg = config or VoiceSessionConfig()
        self._recording = False
        self._buffer = bytearray()
        self._silence_bytes = 0

    @property
    def recording(self) -> bool:
        return self._recording

    def push(self, frame: bytes) -> list[dict]:
        """Process one PCM frame; return events to send to the client."""
        if not frame:
            return []
        return self._record(frame) if self._recording else self._listen(frame)

    # --- States ------------------------------------------------------------

    def _listen(self, frame: bytes) -> list[dict]:
        try:
            detected = self._wake.detect(frame)
        except WakeWordError as exc:
            return [{"event": "error", "detail": str(exc)}]
        if not detected:
            return []
        self._recording = True
        self._buffer = bytearray()
        self._silence_bytes = 0
        return [{"event": "wake_word_detected"}]

    def _record(self, frame: bytes) -> list[dict]:
        self._buffer.extend(frame)
        self._silence_bytes = (
            self._silence_bytes + len(frame) if self._is_silence(frame) else 0
        )
        if self._silence_bytes >= self._bytes_for_ms(self._cfg.silence_ms):
            return self._finalize()
        if len(self._buffer) >= self._bytes_for_ms(self._cfg.max_utterance_ms):
            return self._finalize()
        return []

    def _finalize(self) -> list[dict]:
        pcm = bytes(self._buffer)
        self._recording = False
        self._buffer = bytearray()
        self._silence_bytes = 0
        # Drop a buffer that is effectively all silence (a false trigger).
        if self._is_silence(pcm):
            return [{"event": "listening"}]
        try:
            result = self._stt.transcribe_pcm(
                pcm, sample_rate=self._cfg.sample_rate
            )
        except WhisperError as exc:
            return [{"event": "error", "detail": str(exc)}, {"event": "listening"}]
        return [
            {"event": "transcript", "text": result.text},
            {"event": "listening"},
        ]

    # --- Energy VAD --------------------------------------------------------

    def _is_silence(self, pcm: bytes) -> bool:
        return self._rms(pcm) < self._cfg.silence_rms

    @staticmethod
    def _rms(pcm: bytes) -> float:
        usable = len(pcm) - (len(pcm) % _BYTES_PER_SAMPLE)
        if usable <= 0:
            return 0.0
        samples = array("h")
        samples.frombytes(pcm[:usable])
        total = sum(sample * sample for sample in samples)
        return math.sqrt(total / len(samples))

    def _bytes_for_ms(self, ms: int) -> int:
        return int(self._cfg.sample_rate * _BYTES_PER_SAMPLE * ms / 1000)
