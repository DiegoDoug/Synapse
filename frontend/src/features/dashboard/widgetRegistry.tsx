import { Activity, Bell, Calendar, LayoutGrid } from "lucide-react";

import { NotificationsWidget } from "@/features/dashboard/components/NotificationsWidget";
import { RecentActivityWidget } from "@/features/dashboard/components/RecentActivityWidget";
import { TodaysOverviewWidget } from "@/features/dashboard/components/TodaysOverviewWidget";
import { UpcomingEventsWidget } from "@/features/dashboard/components/UpcomingEventsWidget";
import type { WidgetDefinition, WidgetId } from "@/features/dashboard/types";

/**
 * Single source of truth for every widget the dashboard knows how to render.
 * The grid, the configuration panel, and layout defaults all read from here.
 */
export const WIDGET_DEFINITIONS: Record<WidgetId, WidgetDefinition> = {
  "todays-overview": {
    id: "todays-overview",
    title: "Today's Overview",
    description: "High-level summary of your day.",
    icon: LayoutGrid,
    component: TodaysOverviewWidget,
    defaultSize: { w: 6, h: 3, minW: 3, minH: 3 },
  },
  notifications: {
    id: "notifications",
    title: "Notifications",
    description: "Recent alerts and updates.",
    icon: Bell,
    component: NotificationsWidget,
    defaultSize: { w: 6, h: 3, minW: 3, minH: 2 },
  },
  "upcoming-events": {
    id: "upcoming-events",
    title: "Upcoming Events",
    description: "Your next calendar events.",
    icon: Calendar,
    component: UpcomingEventsWidget,
    defaultSize: { w: 6, h: 3, minW: 3, minH: 3 },
  },
  "recent-activity": {
    id: "recent-activity",
    title: "Recent Activity",
    description: "A feed of recent activity.",
    icon: Activity,
    component: RecentActivityWidget,
    defaultSize: { w: 6, h: 4, minW: 3, minH: 3 },
  },
};

/** Stable display order for widgets (config panel, default placement). */
export const WIDGET_ORDER: WidgetId[] = [
  "todays-overview",
  "notifications",
  "upcoming-events",
  "recent-activity",
];

/** Widgets shown on a fresh dashboard (all of them by default). */
export const DEFAULT_WIDGET_IDS: WidgetId[] = [...WIDGET_ORDER];

/** Type guard: is a persisted id still a known widget? */
export function isWidgetId(value: string): value is WidgetId {
  return value in WIDGET_DEFINITIONS;
}
