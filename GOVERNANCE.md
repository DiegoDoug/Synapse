# Personal OS — Governance Layer

**Instruction precedence:** CURRENT_SPRINT.md > ROADMAP.md > ARCHITECTURE.md > GOVERNANCE.md > CLAUDE.md

This document defines the principles, standards, and philosophy that guide development of Personal OS. These rules influence *how* we build — they do not describe the system itself and are overridden by any active sprint constraint.

| Document | Layer | Overrides |
| -------- | ----- | --------- |
| CURRENT_SPRINT.md | Planning — active stage | Everything |
| ROADMAP.md | Planning — vision | ARCHITECTURE, GOVERNANCE, CLAUDE |
| ARCHITECTURE.md | Runtime — system design | GOVERNANCE, CLAUDE |
| GOVERNANCE.md | Standards — principles | CLAUDE only |
| CLAUDE.md | Instructions — workflow | Nothing |

Related documents:
- **CLAUDE.md** — product vision, workflow, sprint process
- **ARCHITECTURE.md** — runtime system design (overrides this document)
- **ROADMAP.md** — product roadmap (overrides this document)
- **CURRENT_SPRINT.md** — active development stage (overrides everything)

---

## Engineering Philosophy

Act as a senior staff engineer.

Prioritize:

- **maintainability** — code that others can understand and modify
- **modularity** — loosely coupled, highly cohesive components
- **simplicity** — prefer obvious solutions over clever ones
- **scalability** — design for growth without redesign
- **developer experience** — fast feedback, clear patterns, minimal friction

**Core principles:**

- Never optimize prematurely.
- Build only what the current sprint requires.
- Avoid unnecessary abstractions.
- Three similar lines is better than a premature abstraction.

---

## Design Principles

Guidance for the user-facing product:

- **Dark mode first** — design the dark theme, then light
- **Mobile responsive** — desktop-first is outdated; mobile is the constraint
- **Minimal design** — every UI element must earn its place
- **Small components** — single responsibility, composable
- **Strong typing** — leverage type systems to catch errors early
- **Async APIs** — never block user interactions
- **Clear separation of concerns** — UI, logic, data are distinct layers

**Design inspiration:**

- Linear (clean, minimal UX)
- Vercel (focus on essentials)
- Arc Browser (context-aware navigation)
- Raycast (keyboard-first, lightning-fast)

---

## Coding Standards

### Python

- **Type hints everywhere** — use Python 3.12+ `from typing import` and PEP 484
- **Small functions** — aim for <20 lines; if longer, split
- **Dependency injection** — pass dependencies, don't fetch them globally

### TypeScript

- **Strict mode** — `strict: true` in `tsconfig.json`, no `any` without justification
- **Avoid any** — use `unknown` when the type is truly unknown
- **Functional components** — React hooks, not class components

---

## Output Rules

When implementing features or changes:

- **Explain architectural decisions** — why this approach, not alternatives
- **Show affected files** — list what was created or modified
- **Keep files small** — prefer many small files over fewer large ones
- **Do not generate unnecessary code** — YAGNI (You Aren't Gonna Need It)
- **Always build incrementally** — small, testable, reviewable changes
- **Do not proceed beyond CURRENT_SPRINT.md** — stay focused on the active stage
