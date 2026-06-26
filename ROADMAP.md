# Personal OS Roadmap

## Vision

Create an AI-powered personal operating system that centralizes:

- email
- calendars
- tasks
- university resources
- documents
- notifications
- AI assistants
- automations

---

# Stage 1: Foundation

Goals:

- repository structure
- frontend setup
- backend setup
- dashboard layout
- sidebar
- navigation
- theme support
- database setup

Deliverables:

- working frontend
- working backend
- API health endpoint
- dashboard UI

---

# Stage 2: Integrations

Goals:

- Gmail integration
- Google Calendar
- account connections
- synchronization services

Deliverables:

- email synchronization
- calendar synchronization
- connection management

---

# Stage 3: Notifications

Goals:

- Telegram bot
- push notifications
- notification center

Capabilities:

- daily summaries
- reminders
- alerts
- commands

---

# Stage 4: AI Layer

Goals:

- AI chat interface
- multi-provider LLM routing
- prompt system
- tool use framework (function calling infrastructure)
- read-only AI tools
- informational web browsing

Stack:

- Anthropic API (Claude — primary)
- OpenAI API (GPT — secondary)
- Ollama (local inference)
- Open WebUI

Capabilities:

- chat with context
- summarization
- question answering
- recommendations
- tool_use / function calling via Anthropic API
- read tools: search emails, get calendar events, get tasks
- web lookup: navigate URLs and extract content (Playwright, read-only)

Architecture:

- ToolRegistry: maps tool names to backend service calls
- AIService: routes prompts to provider, handles tool_use loop
- BrowserService: Playwright headless instance (read-only in this stage)
- Streaming responses via SSE

---

# Stage 4.5: AI Actions

Goals:

- confirmation system for destructive operations
- write tools: internal CRUD via AI
- write tools: external API writes via AI
- Playwright browser interaction (read + limited write)

Stack:

- Playwright (Python)
- WebSocket or polling for confirmation flow
- PendingAction model (DB)

Capabilities:

Write tools — Internal:
- create_task
- update_task
- delete_task
- update_widget_config

Write tools — External (requires Stage 2 OAuth):
- send_email (Gmail)
- create_calendar_event (Google Calendar)
- delete_calendar_event
- send_telegram_message

Confirmation model:
- Reads: autonomous (no confirmation)
- Creates: autonomous
- Updates: require user approval before execution
- Deletes: require user approval before execution

Browser tools:
- navigate_url (read content)
- extract_structured_data (scrape)
- fill_form + submit (with confirmation)
- take_screenshot (returns image to AI context)

Architecture:

- PendingAction: DB model storing proposed action + payload + status
- ConfirmationService: creates pending actions, listens for approval
- ToolExecutor: runs approved actions through service layer
- ConfirmationModal: frontend component that surfaces pending actions

---

# Stage 4.7: Voice Interface

Goals:

- speech-to-text (STT) via local Whisper
- text-to-speech (TTS) via local Kokoro
- push-to-talk voice chat with the AI
- wake word mode (opt-in, browser-side)
- voice settings panel

Stack:

- faster-whisper (Python) — local STT, no data leaves device
- kokoro (Python) — local TTS, Apache 2.0, natural quality
- openwakeword (Python) — open source wake word detection, Apache 2.0, server-side
- MediaRecorder API (browser) — audio capture for push-to-talk
- AudioWorklet (browser) — raw PCM streaming over WebSocket for wake word mode
- Web Audio API (browser) — waveform visualization + TTS playback
- FastAPI WebSocket — `/ws/voice` bidirectional audio + event channel

Capabilities:

- push-to-talk: hold button → record → release → transcribe → inject into AI chat
- AI response auto-read: TTS plays back AI text response after transcription
- wake word mode: "Hey Synapse" triggers recording without touching the UI
  - opt-in toggle in settings
  - audio is streamed to backend continuously via WebSocket
  - openWakeWord runs inference on each audio frame server-side
  - on detection: backend sends {"event": "wake_word_detected"} back to browser
  - browser enters recording mode; audio continues streaming until silence
- voice session: STT transcript + AI response + TTS logged as a voice interaction

Data flow — Push-to-Talk:

1. User holds VoiceButton
2. MediaRecorder captures audio → WebM blob
3. POST /api/v1/voice/transcribe → faster-whisper → returns text
4. Text injected into AI chat → AI service
5. AI response text → POST /api/v1/voice/synthesize → Kokoro → WAV stream
6. Browser plays audio response

Data flow — Wake Word mode:

1. AudioWorklet streams raw 16kHz PCM chunks → WebSocket /ws/voice
2. Backend WakeWordService runs openWakeWord on each frame
3. Wake word detected → WebSocket sends {"event": "wake_word_detected"}
4. Browser enters recording mode; continues streaming audio
5. WebrtcVAD or silence threshold detects end of utterance
6. Buffered audio → faster-whisper → transcript returned via WebSocket
7. Same AI → TTS pipeline as push-to-talk

Architecture:

- STTService (backend): faster-whisper wrapper, model loaded at startup
- TTSService (backend): Kokoro wrapper, streams audio chunks
- WakeWordService (backend): openWakeWord inference loop on PCM frames
- VoiceWebSocket (backend): ws/voice.py — receives PCM, runs wake word, returns events
- VoiceButton (frontend): push-to-talk UI with waveform animation
- AudioStreamer (frontend): AudioWorklet → encodes PCM → sends over WebSocket
- useVoice hook: unified state machine for both push-to-talk and wake word modes
- VoiceSettings: model selector (tiny/small/medium), voice selector, wake word toggle

Whisper model sizes (user selectable in settings):
- tiny: fastest, lower accuracy (~75 MB)
- small: default, good balance (~466 MB)
- medium: high accuracy, slower (~1.5 GB)

---

# Stage 5: Knowledge System

Goals:

- document uploads
- embeddings
- vector search
- RAG integration with AI chat

Technologies:

- Qdrant
- sentence-transformers
- RAG pipelines

Capabilities:

- semantic search
- document QA
- AI answers grounded in personal knowledge base

---

# Stage 6: Agents

Agents:

- Email Agent
- Calendar Agent
- Study Agent
- Notification Agent

Capabilities:

- autonomous multi-step workflows using Stage 4.5 tools
- task generation
- prioritization
- agents compose tool calls without per-action confirmation

Note: agents operate with elevated autonomy. Destructive operations still
log to audit trail but bypass interactive confirmation.

---

# Stage 7: Automation ✅ Complete

Stack:

- APScheduler
- Playwright (full automation mode)

Capabilities:

- scheduled workflows (interval / cron / event / manual triggers)
- event-driven triggers (new email, calendar event, notification)
- workflow composer: chain agents and tools into named multi-step sequences
- per-step run-history trail with status and error visibility
- schedule personalization: frequency, time, and run-cap controls

---

# Stage 8: Production (Active)

Stack:

- PostgreSQL (replaces SQLite)
- Redis (cache, task queue)
- Docker Compose

Goals:

- deployment
- caching
- horizontal scaling
- audit logs for all AI actions

---

# Future Features

- local models (expanded Ollama support)
- computer use (Anthropic API) for general UI control
- mobile application with voice (native STT/TTS)
- multi-user support
- browser extension for real-time page access
- custom openWakeWord model training for personalized wake phrases
- custom Kokoro voice fine-tuning
- real-time streaming STT (word-by-word transcription via WebSocket)

---

# Success Criteria

Personal OS should become:

- dashboard
- assistant
- memory system
- automation platform
- personal command center
