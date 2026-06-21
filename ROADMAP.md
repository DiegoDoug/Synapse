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

# Stage 7: Automation

Stack:

- APScheduler
- Playwright (full automation mode)

Capabilities:

- scheduled workflows
- event-driven triggers
- Playwright automation: form filling, web scraping pipelines, site monitoring
- workflow composer: chain tools into named automation sequences

Examples:

- create tasks from incoming emails (scheduled)
- detect deadlines in emails, create calendar events
- schedule daily reminders via Telegram
- scrape a webpage on a schedule and summarize changes
- fill and submit a form on a trigger

---

# Stage 8: Production

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

- voice assistant
- local models (expanded Ollama support)
- computer use (Anthropic API) for general UI control
- mobile application
- multi-user support
- browser extension for real-time page access

---

# Success Criteria

Personal OS should become:

- dashboard
- assistant
- memory system
- automation platform
- personal command center
