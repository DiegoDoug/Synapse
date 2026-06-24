/** Presentation helpers for notifications (no network/state). */

import { AlertTriangle, Bell, CalendarClock, Mail } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { NotificationDto } from "@/features/notifications/api";

/** Pick an icon for a notification based on its source, then category. */
export function notificationIcon(notification: NotificationDto): LucideIcon {
  if (notification.source === "email") return Mail;
  if (notification.source === "calendar") return CalendarClock;
  if (notification.category === "alert") return AlertTriangle;
  return Bell;
}

const RELATIVE = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

const DIVISIONS: { amount: number; unit: Intl.RelativeTimeFormatUnit }[] = [
  { amount: 60, unit: "second" },
  { amount: 60, unit: "minute" },
  { amount: 24, unit: "hour" },
  { amount: 7, unit: "day" },
  { amount: 4.34524, unit: "week" },
  { amount: 12, unit: "month" },
  { amount: Number.POSITIVE_INFINITY, unit: "year" },
];

/** Format an ISO timestamp as a compact relative time (e.g. "3 hours ago"). */
export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  let duration = (date.getTime() - Date.now()) / 1000;
  for (const division of DIVISIONS) {
    if (Math.abs(duration) < division.amount) {
      return RELATIVE.format(Math.round(duration), division.unit);
    }
    duration /= division.amount;
  }
  return "";
}
