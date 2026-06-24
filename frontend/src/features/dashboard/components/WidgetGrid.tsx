import { X } from "lucide-react";
import { useMemo } from "react";
import { Responsive, WidthProvider, type Layouts } from "react-grid-layout";

import {
  GRID_BREAKPOINTS,
  GRID_COLS,
  GRID_MARGIN,
  GRID_ROW_HEIGHT,
} from "@/features/dashboard/layout";
import { useDashboardStore } from "@/features/dashboard/stores/useDashboardStore";
import type { DashboardLayouts, WidgetId } from "@/features/dashboard/types";
import { WIDGET_DEFINITIONS } from "@/features/dashboard/widgetRegistry";
import { cn } from "@/lib/utils";

// WidthProvider measures the container so the grid is responsive to its parent.
const ResponsiveGridLayout = WidthProvider(Responsive);

/**
 * Draggable, resizable dashboard grid backed by react-grid-layout.
 * Drag/resize are enabled only in edit mode; layout changes persist locally
 * through the dashboard store.
 */
export function WidgetGrid() {
  const isEditing = useDashboardStore((state) => state.isEditing);
  const activeWidgetIds = useDashboardStore((state) => state.activeWidgetIds);
  const layouts = useDashboardStore((state) => state.layouts);
  const setLayouts = useDashboardStore((state) => state.setLayouts);
  const removeWidget = useDashboardStore((state) => state.removeWidget);

  // react-grid-layout mutates/echoes the layout objects; memo keeps the prop
  // identity stable between renders that don't change the stored layout.
  const gridLayouts = useMemo<Layouts>(() => layouts as Layouts, [layouts]);

  if (activeWidgetIds.length === 0) {
    return (
      <div className="flex min-h-48 items-center justify-center rounded-lg border border-dashed border-border text-sm text-muted-foreground">
        No widgets on your dashboard. Enter edit mode to add some.
      </div>
    );
  }

  return (
    <ResponsiveGridLayout
      className={cn("-m-2", isEditing && "dashboard-grid-editing")}
      layouts={gridLayouts}
      breakpoints={GRID_BREAKPOINTS}
      cols={GRID_COLS}
      rowHeight={GRID_ROW_HEIGHT}
      margin={GRID_MARGIN}
      isDraggable={isEditing}
      isResizable={isEditing}
      draggableCancel=".widget-no-drag"
      compactType="vertical"
      onLayoutChange={(_, allLayouts) => setLayouts(allLayouts as DashboardLayouts)}
    >
      {activeWidgetIds.map((id) => (
        <div key={id} className="h-full">
          <WidgetItem id={id} isEditing={isEditing} onRemove={removeWidget} />
        </div>
      ))}
    </ResponsiveGridLayout>
  );
}

interface WidgetItemProps {
  id: WidgetId;
  isEditing: boolean;
  onRemove: (id: WidgetId) => void;
}

/** Renders one widget plus its edit-mode chrome (remove button). */
function WidgetItem({ id, isEditing, onRemove }: WidgetItemProps) {
  const definition = WIDGET_DEFINITIONS[id];
  const WidgetComponent = definition.component;

  return (
    <div className={cn("relative h-full", isEditing && "cursor-grab active:cursor-grabbing")}>
      {isEditing && (
        <button
          type="button"
          // `widget-no-drag` tells react-grid-layout to ignore drags here.
          className="widget-no-drag absolute right-2 top-2 z-10 inline-flex h-6 w-6 items-center justify-center rounded-md border border-border bg-background text-muted-foreground shadow-sm transition-colors hover:bg-destructive hover:text-destructive-foreground"
          onClick={() => onRemove(id)}
          aria-label={`Remove ${definition.title}`}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
      <WidgetComponent />
    </div>
  );
}
