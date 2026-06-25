# Current Sprint

Current Stage: Stage 4.7

Objective:

Give Personal OS a **voice interface**: local speech-to-text and text-to-speech
so the user can talk to the assistant. Add push-to-talk (hold to record →
transcribe → inject into the existing AI chat → read the reply back) and an
opt-in "Hey Synapse" wake-word mode. All inference is local — no audio leaves the
device.

This is a backend-plus-frontend stage. It builds on the Stage 4 `AIService` +
tool-use loop and the Stage 4.5 confirmation flow (voice injects text into the
exact same chat path, so tool use and confirmations work unchanged), all under
the ARCHITECTURE.md Service → Integration contract.

---

# Allowed Features

Backend:

- a `STTService` (faster-whisper wrapper) — model loaded at startup, selectable
  size (tiny / small / medium)
- a `TTSService` (Kokoro wrapper) — streams synthesized audio chunks
- a `WakeWordService` (openWakeWord) — runs inference on PCM frames, server-side
- a `/ws/voice` WebSocket — receives PCM, runs wake-word detection, returns
  events
- REST: `POST /voice/transcribe` (audio → text), `POST /voice/synthesize`
  (text → audio stream)

Frontend:

- a `VoiceButton` — push-to-talk UI with waveform animation
- an `AudioStreamer` — AudioWorklet that encodes PCM and streams over WebSocket
- a `useVoice` hook — unified state machine for push-to-talk and wake-word modes
- a `VoiceSettings` panel — model-size selector, voice selector, wake-word toggle

---

# Data Flow

Push-to-talk:

1. User holds the `VoiceButton`; `MediaRecorder` captures audio → WebM blob
2. `POST /voice/transcribe` → faster-whisper → transcript text
3. Transcript injected into the existing AI chat (Stage 4/4.5 path, unchanged)
4. AI reply text → `POST /voice/synthesize` → Kokoro → WAV stream
5. Browser plays the audio reply

Wake-word mode (opt-in):

1. `AudioStreamer` streams raw 16 kHz PCM → `/ws/voice`
2. `WakeWordService` runs openWakeWord on each frame
3. On detection the WebSocket sends `{"event": "wake_word_detected"}`
4. Browser enters recording mode; audio continues until a silence threshold
5. Buffered audio → faster-whisper → transcript → same AI → TTS pipeline

---

# Architecture Contract

- **Integration / model layer** — the Whisper, Kokoro, and openWakeWord wrappers
  stay thin; heavy models load lazily so the app still boots without the voice
  dependencies installed (mirror the Stage 4 Playwright / SDK degradation).
- **Service layer** — `STTService`, `TTSService`, and `WakeWordService` own the
  business logic; routes and the WebSocket handler stay thin.
- **Voice reuses the AI path.** Transcripts are injected into the existing
  `AIService` chat flow — voice adds **no** new tool, write, or confirmation
  logic. Tool use and Stage 4.5 confirmations work unchanged.
- A voice interaction (STT transcript + AI reply + TTS) is logged like a normal
  chat turn.

---

# Restrictions

DO NOT implement:

- agents / agent orchestration — Stage 6
- embeddings, vector search, RAG — Stage 5
- workflow automation / scheduled Playwright automation — Stage 7
- PostgreSQL / Redis / Docker — Stage 8
- new write tools or changes to the Stage 4.5 confirmation flow (voice only
  injects text into the existing chat path)
- cloud STT/TTS — all inference is local; no audio leaves the device

Do not implement future stages beyond Stage 4.7.

---

# Deliverables

- `STTService` (faster-whisper) + `TTSService` (Kokoro) + `WakeWordService`
  (openWakeWord)
- `/voice/transcribe` + `/voice/synthesize` REST endpoints and the `/ws/voice`
  WebSocket
- push-to-talk end to end (record → transcribe → AI reply → spoken reply)
- opt-in wake-word mode end to end
- `VoiceButton`, `AudioStreamer`, `useVoice`, and `VoiceSettings` in the UI

---

# Development Process

Build incrementally and pause for approval between major features:

Major Feature 1:
`STTService` + `TTSService` + the `/voice/transcribe` and `/voice/synthesize`
REST endpoints, plus push-to-talk in the UI (`VoiceButton`, `useVoice`,
`VoiceSettings`) wired into the existing AI chat.

Major Feature 2:
`WakeWordService` + the `/ws/voice` WebSocket + the `AudioStreamer`, delivering
the opt-in "Hey Synapse" wake-word mode.

After each major feature:

- explain decisions
- list files created / modified
- wait for approval
