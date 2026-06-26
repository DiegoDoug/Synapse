/** Presentation helpers for workflows — schedule summary, status chips, dates. */

import type { ScheduleKind, Workflow, WorkflowRunStatus } from "./api";

interface ChipMeta {
  label: string;
  /** Tailwind classes for the badge. */
  className: string;
}

export function runStatusMeta(status: WorkflowRunStatus | string): ChipMeta {
  switch (status) {
    case "completed":
      return {
        label: "Completed",
        className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
      };
    case "running":
      return {
        label: "Running…",
        className: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
      };
    case "failed":
      return { label: "Failed", className: "bg-destructive/15 text-destructive" };
    default:
      return { label: status, className: "bg-muted text-muted-foreground" };
  }
}

const SCHEDULE_LABELS: Record<ScheduleKind, string> = {
  manual: "On demand",
  interval: "Repeating",
  cron: "Daily",
  event: "On event",
};

export function scheduleKindLabel(kind: ScheduleKind | string): string {
  return SCHEDULE_LABELS[kind as ScheduleKind] ?? kind;
}

const EVENT_LABELS: Record<string, string> = {
  new_email: "a new email is synced",
  new_calendar_event: "a new calendar event is synced",
  new_notification: "a new notification is raised",
};

export function eventLabel(eventType: string | null): string {
  if (!eventType) return "an event";
  return EVENT_LABELS[eventType] ?? eventType;
}

/** A human one-liner describing *when / how often* a workflow runs. */
export function scheduleSummary(workflow: Workflow): string {
  if (workflow.schedule_kind === "interval" && workflow.interval_minutes) {
    return `Every ${formatInterval(workflow.interval_minutes)}`;
  }
  if (workflow.schedule_kind === "cron" && workflow.cron_hour !== null) {
    return `Daily at ${formatClock(workflow.cron_hour, workflow.cron_minute ?? 0)} UTC`;
  }
  if (workflow.schedule_kind === "event") {
    return `When ${eventLabel(workflow.event_type)}`;
  }
  return "Runs only when you trigger it";
}

/** "3 steps" / "1 step" caption for the composed sequence. */
export function stepsSummary(workflow: Workflow): string {
  const n = workflow.steps.length;
  return `${n} step${n === 1 ? "" : "s"}`;
}

/** Caption for the run cap ("how many times"). */
export function runCapSummary(workflow: Workflow): string {
  if (workflow.max_runs === null) {
    return `${workflow.run_count} run${workflow.run_count === 1 ? "" : "s"}`;
  }
  return `${workflow.run_count} / ${workflow.max_runs} runs`;
}

function formatInterval(minutes: number): string {
  if (minutes % 1440 === 0) {
    const days = minutes / 1440;
    return days === 1 ? "day" : `${days} days`;
  }
  if (minutes % 60 === 0) {
    const hours = minutes / 60;
    return hours === 1 ? "hour" : `${hours} hours`;
  }
  return minutes === 1 ? "minute" : `${minutes} minutes`;
}

function formatClock(hour: number, minute: number): string {
  const hh = String(hour).padStart(2, "0");
  const mm = String(minute).padStart(2, "0");
  return `${hh}:${mm}`;
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}
