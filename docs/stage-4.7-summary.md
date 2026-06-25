# Stage 4.7 Summary — Voice Interface

**Status:** Complete
**Outcome:** Personal OS can now be operated by voice, entirely locally. Hold a
button to talk (push-to-talk) or enable hands-free "wake word" listening; either
way the spoken request is transcribed and **injected into the existing AI chat**,
so voice reuses the Stage 4 tool-use loop and the Stage 4.5 confirmation flow
unchanged. Replies can be read back aloud. No audio leaves the device — STT
(faster-whisper), TTS (Kokoro), and wake word (openWakeWord) all run on the
server, lazily loaded so the app still boots without them.

This is a backend-plus-frontend stage. No agents, RAG/embeddings, or scheduled
automation were introduced (deferred to Stages 6 / 5 / 7).

Stage 4.7 was delivered in two major features (each merged via PR), gated by CI:

- **Major Feature 1 — push-to-talk STT/TTS** (PR #18): Whisper/Kokoro clients +
  `STTService`/`TTSService`, `/voice/{config,transcribe,synthesize}`, a
  `VoiceButton` and read-aloud toggle wired into the Assistant.
- **Major Feature 2 — wake-word mode** (PR #19): openWakeWord client +
  `WakeWordService`, a transport-agnostic `VoiceSession` state machine + energy
  VAD, the `/voice/ws` WebSocket, an `AudioStreamer` (AudioWorklet) + wake-word
  toggle.

---

## Objectives Completed

- **Local STT** — `WhisperClient` (faster-whisper) + `STTService`; transcribes
  uploaded clips and raw 16 kHz PCM (`transcribe_pcm`).
- **Local TTS** — `KokoroClient` + `TTSService`; assembles WAV from the model's
  float32 chunks with the stdlib `wave` module.
- **Wake word** — `OpenWakeWordClient` + `WakeWordService`; per-frame scoring
  against a configurable threshold.
- **`VoiceSession`** — a transport-agnostic `listening → recording → transcript`
  state machine with a dependency-free energy VAD for end-of-utterance, emitting
  `wake_word_detected` / `transcript` / `listening` / `error` events.
- **API** — `GET /voice/config` (capabilities + settings), `POST
  /voice/transcribe`, `POST /voice/synthesize` (WAV stream), and the `WS
  /voice/ws` wake-word channel (inference run off the event loop).
- **Frontend** — `useVoice` (push-to-talk over MediaRecorder + TTS playback),
  `VoiceButton`, an `AudioStreamer` (AudioWorklet → 16 kHz PCM over WebSocket) +
  `useWakeWord`, a `VoiceSettings` panel, and Assistant wiring with a listening
  indicator and read-aloud of replies.
- **Graceful degradation everywhere** — the optional model packages are lazily
  imported; REST returns 503, the WebSocket sends `unavailable`, and the UI
  gates its controls when they're absent.

---

## Files Created

**Major Feature 1**

- `backend/integrations/voice/{__init__,whisper,kokoro}.py`
- `backend/services/{stt_service,tts_service}.py`
- `backend/schemas/voice.py`, `backend/api/routes/voice.py`
- `backend/requirements-voice.txt`, `backend/tests/test_stage47_voice.py`
- `frontend/src/features/voice/{api.ts,useVoice.ts,VoiceSettings.tsx}`
- `frontend/src/components/ai/VoiceButton.tsx`

**Major Feature 2**

- `backend/integrations/voice/wakeword.py`
- `backend/services/{wakeword_service,voice_session}.py`
- `backend/tests/test_stage47_wakeword.py`
- `frontend/public/pcm-worklet.js`
- `frontend/src/features/voice/{AudioStreamer.ts,useWakeWord.ts}`

**Docs**

- `docs/stage-4.7-summary.md` — this file

## Files Modified

- `backend/config.py` — Whisper / Kokoro / wake-word + VAD settings
- `backend/integrations/voice/whisper.py` — `transcribe_pcm` (MF2)
- `backend/services/stt_service.py` — `transcribe_pcm` (MF2)
- `backend/integrations/voice/__init__.py` — export the wake-word client (MF2)
- `backend/api/routes/voice.py` — `/voice/ws` + config availability (MF2)
- `backend/schemas/voice.py` — wake-word fields on `VoiceConfig` (MF2)
- `backend/services/factory.py` — cached voice client singletons + builders
- `backend/api/dependencies.py` — STT / TTS / wake-word service providers
- `backend/api/routes/__init__.py` — mount the voice router
- `backend/pyproject.toml` — ruff exempt `fastapi.File`
- `backend/requirements{,-voice}.txt` — `python-multipart`; optional voice deps
- `frontend/src/pages/AssistantPage.tsx` — voice button, auto-read, wake-word arm
- `frontend/src/pages/SettingsPage.tsx` — mount `VoiceSettings`
- `frontend/src/store/useAppStore.ts` — `voiceAutoRead` + `voiceWakeWord`
- `frontend/src/features/voice/{api.ts,VoiceSettings.tsx}` — wake-word config
- `frontend/vite.config.ts` — proxy WebSocket upgrades (`ws: true`)
- `CURRENT_SPRINT.md` — Stage 4.7 spec, then advanced to Stage 5

---

## Architectural Decisions

- **Voice reuses the AI path; it adds nothing to it.** Both push-to-talk and
  wake word inject a transcript into the existing `send`/`AIService` flow, so
  tool use and Stage 4.5 confirmations work with zero new logic.
- **Heavy ML deps are opt-in.** faster-whisper, Kokoro, and openWakeWord pull
  PyTorch/CTranslate2; they live in `requirements-voice.txt`, are lazily
  imported, and degrade gracefully — keeping the base install and CI lean
  (the established Playwright/SDK pattern).
- **Model clients are process singletons.** Built once in the factory so each
  heavy model loads a single time, not per request.
- **`VoiceSession` is transport-agnostic.** The wake-word state machine is a
  plain class (`push(frame) → events`), unit-tested without a WebSocket; the
  route is a thin driver. End-of-utterance uses a stdlib RMS energy VAD (no
  numpy, no deprecated `audioop`).
- **WebSocket inference runs off the event loop** via `run_in_threadpool`, so a
  blocking transcription never stalls the async server.
- **Generic, capability-gated UI.** `/voice/config` reports availability for
  each capability; the settings toggles and Assistant controls disable
  themselves when a model isn't installed.

---

## Verification

- `ruff check backend/` — passes
- `python -m pytest backend/tests/` — **92 passed** (18 voice + prior 74)
- STT/TTS/wake-word services, the VAD state machine, the `/voice/ws` protocol,
  and graceful degradation all exercised with in-memory fakes — no models,
  audio decoding, or network in tests
- Frontend `tsc -b`, `vite build`, and `eslint` all clean
- CI (GitHub Actions) green on PRs #18 and #19

---

## Unresolved Issues / Technical Debt

- **Not verified against real models.** Whisper/Kokoro/openWakeWord are
  implemented to spec and tested with fakes, but not run against installed
  models here; first real transcription / synthesis / detection should be
  smoke-tested after `pip install -r backend/requirements-voice.txt`.
- **No personalized wake phrase.** openWakeWord ships pretrained models (default
  `hey_jarvis`); a custom "Hey Synapse" needs model training (ROADMAP future
  work). UI copy stays generic ("wake word").
- **Energy VAD, not WebRTC VAD.** Simple and robust for a prototype; a stricter
  voice-activity detector is an easy later swap.
- **Model size / voice are env-config, read-only in the UI.** Runtime selection
  would need settings-write endpoints.
- **Single-user scoping.** Voice endpoints are unauthenticated like the rest of
  the app; per-user isolation waits on an auth stage.
- **WebSocket blocks the loop during model load.** The first frame after connect
  pays the (one-time) model-load cost on a worker thread; acceptable, but a warm
  load at startup would smooth the first interaction.

---

## Recommendations for Stage 5 (Knowledge System)

- Add a **document ingestion** path: upload → text extraction → chunking →
  embeddings (sentence-transformers) → vector store (Qdrant), behind a
  `DocumentService` + an embeddings/vector **integration** per the
  Service → Integration contract.
- Expose **semantic search** and ground AI answers via a **retrieval tool** in
  the existing `ToolRegistry`, so RAG reuses the Stage 4 tool-use loop (no
  changes to the chat/confirmation core).
- Keep heavy deps (sentence-transformers, Qdrant client) **lazy/optional** with
  graceful degradation, mirroring the voice + browser pattern; consider an
  in-process fallback so the app runs without a Qdrant server during early dev.
- Surface uploaded documents and citations in the UI; cite retrieved chunks in
  answers for traceability.
