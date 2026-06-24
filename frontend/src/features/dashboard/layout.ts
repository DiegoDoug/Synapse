import type { Layout } from "react-grid-layout";

import type { Breakpoint, DashboardLayouts, WidgetId } from "@/features/dashboard/types";
import { WIDGET_DEFINITIONS } from "@/features/dashboard/widgetRegistry";

/** Pixel widths at which the grid switches column counts. */
export const GRID_BREAKPOINTS: Record<Breakpoint, number> = {
  lg: 1024,
  md: 768,
  sm: 480,
  xs: 0,
};

/** Number of columns available at each breakpoint. */
export const GRID_COLS: Record<Breakpoint, number> = {
  lg: 12,
  md: 8,
  sm: 4,
  xs: 2,
};

/** Default widget width (in columns) per breakpoint. */
const WIDGET_WIDTH: Record<Breakpoint, number> = {
  lg: 6,
  md: 4,
  sm: 4,
  xs: 2,
};

export const GRID_ROW_HEIGHT = 72;
export const GRID_MARGIN: [number, number] = [16, 16];

const BREAKPOINTS: Breakpoint[] = ["lg", "md", "sm", "xs"];

/** Build a single breakpoint's layout by flowing widgets left-to-right. */
function buildBreakpointLayout(ids: WidgetId[], breakpoint: Breakpoint): Layout[] {
  const cols = GRID_COLS[breakpoint];
  const width = Math.min(WIDGET_WIDTH[breakpoint], cols);
  const perRow = Math.max(1, Math.floor(cols / width));

  return ids.map((id, index) => {
    const { defaultSize } = WIDGET_DEFINITIONS[id];
    return {
      i: id,
      x: (index % perRow) * width,
      y: Math.floor(index / perRow) * defaultSize.h,
      w: width,
      h: defaultSize.h,
      minW: Math.min(defaultSize.minW, cols),
      minH: defaultSize.minH,
    };
  });
}

/** Generate a full responsive layout set for the given widgets. */
export function buildDefaultLayouts(ids: WidgetId[]): DashboardLayouts {
  return BREAKPOINTS.reduce((acc, breakpoint) => {
    acc[breakpoint] = buildBreakpointLayout(ids, breakpoint);
    return acc;
  }, {} as DashboardLayouts);
}

/** Append a newly added widget to every breakpoint (stacked at the bottom). */
export function addWidgetToLayouts(
  layouts: DashboardLayouts,
  id: WidgetId,
): DashboardLayouts {
  const { defaultSize } = WIDGET_DEFINITIONS[id];
  return BREAKPOINTS.reduce((acc, breakpoint) => {
    const existing = layouts[breakpoint] ?? [];
    if (existing.some((item) => item.i === id)) {
      acc[breakpoint] = existing;
      return acc;
    }
    const cols = GRID_COLS[breakpoint];
    const width = Math.min(WIDGET_WIDTH[breakpoint], cols);
    const maxY = existing.reduce((max, item) => Math.max(max, item.y + item.h), 0);
    acc[breakpoint] = [
      ...existing,
      {
        i: id,
        x: 0,
        y: maxY,
        w: width,
        h: defaultSize.h,
        minW: Math.min(defaultSize.minW, cols),
        minH: defaultSize.minH,
      },
    ];
    return acc;
  }, {} as DashboardLayouts);
}

/** Drop a widget from every breakpoint's layout. */
export function removeWidgetFromLayouts(
  layouts: DashboardLayouts,
  id: WidgetId,
): DashboardLayouts {
  return BREAKPOINTS.reduce((acc, breakpoint) => {
    acc[breakpoint] = (layouts[breakpoint] ?? []).filter((item) => item.i !== id);
    return acc;
  }, {} as DashboardLayouts);
}
