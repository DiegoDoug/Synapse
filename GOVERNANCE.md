# Personal OS — Governance Layer

This document defines the principles, standards, and philosophy that guide development of Personal OS. These rules influence how we build the system, but do not describe the system itself.

See:
- **CLAUDE.md** for product vision and instructions
- **ARCHITECTURE.md** for the runtime system design
- **ROADMAP.md** for the product roadmap
- **CURRENT_SPRINT.md** for the active development stage

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
