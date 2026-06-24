# Current Sprint

Current Stage: Stage 1.5

Objective:

Turn the Stage 1 placeholder dashboard into a fully customizable,
drag-and-drop widget grid. Users arrange, resize, add, and remove widgets in
an explicit edit mode, and their layout persists locally across reloads.

This is a frontend-only stage between the Stage 1 foundation and the Stage 2
integrations.

---

# Allowed Features

Frontend:

- react-grid-layout integration (responsive widget grid)
- drag-and-drop widget repositioning
- resize support (per-widget minimum sizes)
- edit mode (toggle drag/resize/remove on and off)
- widget configuration (add / remove which widgets appear)
- local layout persistence (browser storage)

---

# Architecture Contract

Per ARCHITECTURE.md (frontend, feature-based):

- A registry is the single source of truth for available widgets
  (metadata + component + default size).
- Dashboard layout state lives in a dedicated feature store (Zustand),
  separate from the global UI store.
- Server state (React Query) is untouched in this stage.

---

# Restrictions

DO NOT implement:

- backend persistence of layouts (browser-local only)
- new backend models, routes, or services
- integrations / external APIs (Stage 2)
- AI systems / agents, notifications, embeddings, voice

Do not implement future stages beyond Stage 1.5.

---

# Deliverables

- react-grid-layout grid replacing the static placeholder grid
- drag-and-drop repositioning in edit mode
- resize support
- edit mode toggle with reset
- widget configuration (add / remove widgets)
- layouts saved locally and restored on reload

---

# Development Process

Major Feature 1:
react-grid-layout grid + drag-and-drop + resize + edit mode + local persistence.

Major Feature 2:
Widget configuration (add-widget library; inline removal).

After each major feature:

- explain decisions
- list files created
- wait for approval
