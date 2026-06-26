/** Presentation helpers for agent runs — status chips, step icons, dates. */

import {
  AlertTriangle,
  CheckCircle2,
  ListChecks,
  Loader2,
  type LucideIcon,
  Wrench,
} from "lucide-react";

import type { RunStatus, StepKind } from "@/features/agents/api";

interface ChipMeta {
  label: string;
  /** Tailwind classes for the badge. */
  className: string;
}

export function runStatusMeta(status: RunStatus | string): ChipMeta {
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

export function stepIcon(kind: StepKind | string): LucideIcon {
  switch (kind) {
    case "plan":
      return ListChecks;
    case "action":
      return Wrench;
    case "result":
      return CheckCircle2;
    case "error":
      return AlertTriangle;
    default:
      return Loader2;
  }
}

export function formatDateTime(iso: string): string {
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
