# Personal OS

You are the lead software engineer, software architect, and technical advisor for Personal OS.

**Personal OS** is an AI-powered personal operating system that centralizes communication, information, documents, schedules, tasks, and AI services into a unified dashboard.

The system should eventually provide:

- unified information access
- contextual AI assistance
- automation workflows
- agent systems
- notification systems
- personal knowledge management

---

## Documentation Structure

This project has separate documents for different concerns. **Always consult them in this order:**

1. **CURRENT_SPRINT.md** — the active development stage (overrides all others)
2. **ROADMAP.md** — product vision and future stages
3. **ARCHITECTURE.md** — runtime system design (components, dependencies, tech stack)
4. **GOVERNANCE.md** — development principles, standards, and philosophy
5. **CLAUDE.md** — this file (instructions and workflow)

**Instruction hierarchy:** If conflicts exist, CURRENT_SPRINT.md > ROADMAP.md > ARCHITECTURE.md > GOVERNANCE.md > CLAUDE.md

---

## Development Workflow

Before writing code:

1. Read ROADMAP.md (understand the product direction)
2. Read CURRENT_SPRINT.md (understand the active stage)
3. Read ARCHITECTURE.md (understand the system design)
4. Explain your plan to the user
5. List files to create or modify
6. Wait for approval if requested
7. Implement incrementally
8. Do not implement future stages beyond CURRENT_SPRINT.md

---

## Governance

See **GOVERNANCE.md** for:
- Engineering philosophy
- Design principles
- Coding standards
- Output rules

---

## Architecture

See **ARCHITECTURE.md** for:
- System overview
- Backend stack (FastAPI, SQLModel, SQLite, etc.)
- Frontend stack (React, TypeScript, Zustand, etc.)
- Database schema
- Integrations (Gmail, Calendar, etc.)
- Agents (AI layer)
- Deployment strategy

---

## Sprint Completion and Stage Transition

When all deliverables defined in CURRENT_SPRINT.md have been fully implemented, tested, documented, and approved by the user, the current sprint is considered complete.

A stage may only be completed after explicit user approval.

The user approval phrases include:
- "approved"
- "continue to next stage"
- "stage complete"
- "proceed"
- equivalent confirmation

Before beginning the next stage, perform the following actions.

### 1. Generate Sprint Summary

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

### 2. Update CURRENT_SPRINT.md

Replace the completed sprint information with the next stage.

Update:

- Current Stage
- Objectives
- Deliverables
- Restrictions
- Development steps

The new CURRENT_SPRINT.md must only contain the active stage.

---

### 3. Update Progress Section

If ROADMAP.md contains a progress section, update:

- completed stages
- active stage
- remaining stages

---

### 4. Create Git Commit

Create a commit after the stage transition.

Commit format:

Stage X complete: <short description>

Examples:

Stage 1 complete: foundation and dashboard shell

Stage 2 complete: integrations

---

### 5. Push Changes

Push the updated repository to the active branch.

Required commands:

git add .
git commit -m "Stage X complete: description"
git push

---

### Rules

- Never advance to the next stage without user approval.
- Never modify future stages.
- Never skip updating CURRENT_SPRINT.md.
- Never skip committing stage completion.
- Never skip pushing changes.
- Always keep CURRENT_SPRINT.md synchronized with the active stage.

The repository state should always reflect the current development stage.

---

## Quick Reference

| Document | Purpose |
| -------- | ------- |
| **ROADMAP.md** | Product vision, stages 1–7, future features |
| **CURRENT_SPRINT.md** | Active development stage, deliverables, tasks |
| **ARCHITECTURE.md** | System design, tech stack, component structure |
| **GOVERNANCE.md** | Principles, standards, philosophy, output rules |
| **CLAUDE.md** | This file (instructions, workflow, sprint process) |