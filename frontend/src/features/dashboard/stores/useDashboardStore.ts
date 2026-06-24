import { create } from "zustand";
import { persist } from "zustand/middleware";

import {
  addWidgetToLayouts,
  buildDefaultLayouts,
  removeWidgetFromLayouts,
} from "@/features/dashboard/layout";
import type { DashboardLayouts, WidgetId } from "@/features/dashboard/types";
import { DEFAULT_WIDGET_IDS, isWidgetId } from "@/features/dashboard/widgetRegistry";

interface DashboardState {
  /** Whether the dashboard is in layout-editing mode. */
  isEditing: boolean;
  /** Widgets currently placed on the grid (drives what is rendered). */
  activeWidgetIds: WidgetId[];
  /** Per-breakpoint react-grid-layout positions. */
  layouts: DashboardLayouts;

  toggleEditing: () => void;
  setEditing: (editing: boolean) => void;
  /** Persist the layout react-grid-layout reports after drag/resize. */
  setLayouts: (layouts: DashboardLayouts) => void;
  addWidget: (id: WidgetId) => void;
  removeWidget: (id: WidgetId) => void;
  /** Restore the default widget set and layout. */
  resetDashboard: () => void;
}

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set) => ({
      isEditing: false,
      activeWidgetIds: DEFAULT_WIDGET_IDS,
      layouts: buildDefaultLayouts(DEFAULT_WIDGET_IDS),

      toggleEditing: () => set((state) => ({ isEditing: !state.isEditing })),
      setEditing: (editing) => set({ isEditing: editing }),
      setLayouts: (layouts) => set({ layouts }),

      addWidget: (id) =>
        set((state) => {
          if (state.activeWidgetIds.includes(id)) return state;
          return {
            activeWidgetIds: [...state.activeWidgetIds, id],
            layouts: addWidgetToLayouts(state.layouts, id),
          };
        }),

      removeWidget: (id) =>
        set((state) => ({
          activeWidgetIds: state.activeWidgetIds.filter((widgetId) => widgetId !== id),
          layouts: removeWidgetFromLayouts(state.layouts, id),
        })),

      resetDashboard: () =>
        set({
          activeWidgetIds: DEFAULT_WIDGET_IDS,
          layouts: buildDefaultLayouts(DEFAULT_WIDGET_IDS),
        }),
    }),
    {
      name: "synapse-dashboard-layout",
      version: 1,
      // Only persist user data — never the transient edit-mode flag.
      partialize: (state) => ({
        activeWidgetIds: state.activeWidgetIds,
        layouts: state.layouts,
      }),
      // Drop widgets that no longer exist in the registry (forward-compat).
      merge: (persisted, current) => {
        const saved = persisted as Partial<DashboardState> | undefined;
        const activeWidgetIds = (saved?.activeWidgetIds ?? current.activeWidgetIds).filter(
          isWidgetId,
        );
        return {
          ...current,
          ...saved,
          isEditing: false,
          activeWidgetIds,
          layouts: saved?.layouts ?? current.layouts,
        };
      },
    },
  ),
);
