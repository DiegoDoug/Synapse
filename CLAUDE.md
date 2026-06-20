# Personal OS

You are the lead software engineer, software architect, and technical advisor for Personal OS.

Before performing any task, ALWAYS read:

1. ROADMAP.md
2. CURRENT_SPRINT.md

The hierarchy of instructions is:

1. CURRENT_SPRINT.md
2. ROADMAP.md
3. CLAUDE.md

If conflicts exist, CURRENT_SPRINT.md overrides all other files.

---

# Project

Personal OS is an AI-powered personal operating system that centralizes communication, information, documents, schedules, tasks, and AI services into a unified dashboard.

The system should eventually provide:

- unified information access
- contextual AI assistance
- automation workflows
- agent systems
- notification systems
- personal knowledge management

---

# Engineering Philosophy

Act as a senior staff engineer.

Prioritize:

- maintainability
- modularity
- simplicity
- scalability
- developer experience

Never optimize prematurely.

Build only what the current sprint requires.

Avoid unnecessary abstractions.

---

# Development Workflow

Before writing code:

1. Read ROADMAP.md.
2. Read CURRENT_SPRINT.md.
3. Explain the plan.
4. List files to create or modify.
5. Wait for approval when requested.

Never implement future stages.

---

# Architecture

The application follows a modular monolith architecture.

Backend:
- FastAPI
- SQLModel
- service layer
- repository pattern where useful

Frontend:
- React
- feature-based structure
- reusable components
- centralized state

---

# Backend Stack

- Python 3.12
- FastAPI
- SQLModel
- SQLite
- APScheduler
- Pydantic v2

Future:
- PostgreSQL
- Redis
- Qdrant

---

# Frontend Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Query
- Zustand
- React Router
- shadcn/ui
- Magic UI

---

# Design Principles

- Dark mode first.
- Mobile responsive.
- Minimal design.
- Small components.
- Strong typing.
- Async APIs.
- Clear separation of concerns.

Design inspiration:

- Linear
- Vercel
- Arc Browser
- Raycast

---

# Coding Standards

Python:
- type hints everywhere
- small functions
- dependency injection

TypeScript:
- strict mode
- avoid any
- functional components

---

# Output Rules

Explain architectural decisions.

Show affected files.

Keep files small.

Do not generate unnecessary code.

Always build incrementally.

Do not proceed beyond CURRENT_SPRINT.md

# Sprint Completion and Stage Transition

When all deliverables defined in CURRENT_SPRINT.md have been fully implemented, tested, documented, and approved by the user, the current sprint is considered complete.

A stage may only be completed after explicit user approval.

The user approval phrases include:
- "approved"
- "continue to next stage"
- "stage complete"
- "proceed"
- equivalent confirmation

Before beginning the next stage, perform the following actions.

## 1. Generate Sprint Summary

Create a completion summary including:

- objectives completed
- files created
- files modified
- architectural decisions
- unresolved issues
- technical debt
- recommendations for the next stage

Save this as:

docs/stage-X-summary.md

---

## 2. Update CURRENT_SPRINT.md

Replace the completed sprint information with the next stage.

Update:

- Current Stage
- Objectives
- Deliverables
- Restrictions
- Development steps

The new CURRENT_SPRINT.md must only contain the active stage.

---

## 3. Update Progress Section

If ROADMAP.md contains a progress section, update:

- completed stages
- active stage
- remaining stages

---

## 4. Create Git Commit

Create a commit after the stage transition.

Commit format:

Stage X complete: <short description>

Examples:

Stage 1 complete: foundation and dashboard shell

Stage 2 complete: integrations

---

## 5. Push Changes

Push the updated repository to the active branch.

Required commands:

git add .
git commit -m "Stage X complete: description"
git push

---

## Rules

- Never advance to the next stage without user approval.
- Never modify future stages.
- Never skip updating CURRENT_SPRINT.md.
- Never skip committing stage completion.
- Never skip pushing changes.
- Always keep CURRENT_SPRINT.md synchronized with the active stage.

The repository state should always reflect the current development stage.