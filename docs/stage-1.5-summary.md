# Stage 1.5 Summary — Dashboard Customization

**Status:** Complete
**Outcome:** The Stage 1 placeholder dashboard became a fully customizable,
drag-and-drop widget grid. Users can rearrange, resize, add, and remove widgets
in an explicit edit mode, and their layout persists locally across reloads. No
backend was involved — this is a frontend-only stage that sits between the
Stage 1 foundation and the Stage 2 integrations.

---

## Objectives Completed

- Integrated **react-grid-layout** for a responsive widget grid
- **Drag-and-drop** repositioning (edit mode only)
- **Resize** support with per-widget minimum sizes and a themed handle
- **Edit mode** toggle ("Edit layout" / "Done") with a reset action
- **Widget configuration**: add widgets via a library popover, remove inline
- **Local persistence** of layout + active widgets via `zustand` `persist`
  (`localStorage`), no backend writes

---

## Files Created

- `frontend/src/components/ui/button.tsx` — handcrafted shadcn-style button primitive
- `frontend/src/features/dashboard/widgetRegistry.tsx` — single source of truth for widgets (metadata + component + default size)
- `frontend/src/features/dashboard/layout.ts` — grid constants + default/add/remove layout builders
- `frontend/src/features/dashboard/stores/useDashboardStore.ts` — persisted dashboard store (edit mode, active widgets, layouts)
- `frontend/src/features/dashboard/components/DashboardToolbar.tsx` — edit/reset/add controls
- `frontend/src/features/dashboard/components/WidgetLibrary.tsx` — add-widget popover
- `docs/stage-1.5-summary.md` — this file

## Files Modified

- `frontend/src/features/dashboard/components/WidgetGrid.tsx` — rewritten on react-grid-layout
- `frontend/src/features/dashboard/components/WidgetCard.tsx` — fills grid-cell height
- `frontend/src/features/dashboard/types.ts` — widget + layout types
- `frontend/src/pages/DashboardPage.tsx` — toolbar + edit-aware copy
- `frontend/src/main.tsx` — import react-grid-layout / react-resizable CSS
- `frontend/src/styles/globals.css` — dark-first theming for grid placeholder, drag, and resize handle
- `frontend/package.json` / `package-lock.json` — add `react-grid-layout` + types
- `CURRENT_SPRINT.md` — synced to Stage 1.5

---

## Architectural Decisions

- **Registry-driven widgets** — the grid, the add-widget library, and layout
  defaults all read from one `WIDGET_DEFINITIONS` map, so adding a widget is a
  single-file change.
- **Layout state in a dedicated feature store** — `useDashboardStore`
  (Zustand) is separate from the global `useAppStore`, matching the
  ARCHITECTURE "feature store" pattern. The transient `isEditing` flag is
  intentionally *not* persisted (`partialize`), and a `merge` step drops
  widgets that are no longer in the registry (forward-compatible persistence).
- **Whole-card dragging in edit mode** — more intuitive than a small handle;
  the remove button opts out via `draggableCancel=".widget-no-drag"`.
- **CSS imported in `main.tsx`** — react-grid-layout/react-resizable stylesheets
  loaded via JS import (Vite-friendly) rather than CSS `@import`.
- **Frontend-only** — no backend persistence, per the stage constraint; the
  `DashboardWidget` backend model from Stage 1 remains unused for now.

---

## Verification

- `tsc -b` — passes (strict TypeScript, no `any`)
- `eslint .` — passes
- `vite build` — passes
- No browser available in the environment; no DOM/visual assertions performed.

---

## Technical Debt / Notes

- Layout persistence is browser-local only. When Stage 8 or a dedicated
  persistence stage arrives, the `DashboardWidget` backend model can back this
  up server-side; the store shape (`activeWidgetIds` + `layouts`) maps cleanly.
- Widgets are still visual placeholders; real data arrives with Stage 2
  integrations, which can render into the existing widget components unchanged.
- The add-widget popover uses a lightweight backdrop for outside-click; if more
  popovers appear, consider a shared primitive (e.g. shadcn `Popover`).

---

## Recommendations for Stage 2 (Integrations)

- Feed synced Gmail/Calendar data into the existing widget components
  (`UpcomingEventsWidget`, `RecentActivityWidget`, etc.) via React Query —
  no grid changes required.
- Reset `CURRENT_SPRINT.md` to the Stage 2 integrations spec (preserved in git
  history at the previous commit) when starting that stage.
