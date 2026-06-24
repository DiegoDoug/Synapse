import type { LucideIcon } from "lucide-react";
import type { ComponentType } from "react";
import type { Layout } from "react-grid-layout";

/** Stable identifiers for the built-in dashboard widgets. */
export type WidgetId =
  | "todays-overview"
  | "notifications"
  | "upcoming-events"
  | "recent-activity";

/** Static metadata + component for a widget the dashboard can render. */
export interface WidgetDefinition {
  id: WidgetId;
  title: string;
  description: string;
  icon: LucideIcon;
  component: ComponentType;
  /** Default grid footprint used when the widget is first placed. */
  defaultSize: { w: number; h: number; minW: number; minH: number };
}

/** Responsive breakpoint keys (mirror react-grid-layout's configuration). */
export type Breakpoint = "lg" | "md" | "sm" | "xs";

/** Per-breakpoint layout map persisted for the dashboard grid. */
export type DashboardLayouts = Record<Breakpoint, Layout[]>;
