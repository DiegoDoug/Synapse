import {
  Clock,
  Loader2,
  Pencil,
  Play,
  Power,
  Repeat,
  Trash2,
  Zap,
} from "lucide-react";

import type { Workflow } from "@/features/workflows/api";
import {
  runCapSummary,
  scheduleKindLabel,
  scheduleSummary,
  stepsSummary,
} from "@/features/workflows/format";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface WorkflowCardProps {
  workflow: Workflow;
  isSelected: boolean;
  isBusy: boolean;
  onSelect: () => void;
  onRun: () => void;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

/** One workflow: its schedule summary, state, and the lifecycle controls. */
export function WorkflowCard({
  workflow,
  isSelected,
  isBusy,
  onSelect,
  onRun,
  onToggle,
  onEdit,
  onDelete,
}: WorkflowCardProps) {
  const isManual = workflow.schedule_kind === "manual";
  const ScheduleIcon =
    workflow.schedule_kind === "cron"
      ? Clock
      : workflow.schedule_kind === "event"
        ? Zap
        : Repeat;

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 transition-colors",
        isSelected ? "border-primary" : "border-border",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <button type="button" onClick={onSelect} className="min-w-0 text-left">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold">{workflow.name}</h3>
            {!isManual && (
              <span
                className={cn(
                  "shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium",
                  workflow.enabled
                    ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {workflow.enabled ? "Active" : "Paused"}
              </span>
            )}
          </div>
          {workflow.description && (
            <p className="truncate text-xs text-muted-foreground">
              {workflow.description}
            </p>
          )}
        </button>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <ScheduleIcon className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{scheduleSummary(workflow)}</span>
        </div>
        <div className="text-right text-muted-foreground">
          {stepsSummary(workflow)} · {scheduleKindLabel(workflow.schedule_kind)} ·{" "}
          {runCapSummary(workflow)}
        </div>
      </dl>

      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={onRun} disabled={isBusy}>
          {isBusy ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Run now
        </Button>
        {!isManual && (
          <Button size="sm" variant="ghost" onClick={onToggle} disabled={isBusy}>
            <Power className="h-3.5 w-3.5" />
            {workflow.enabled ? "Pause" : "Enable"}
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={onEdit} disabled={isBusy}>
          <Pencil className="h-3.5 w-3.5" />
          Edit
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onDelete}
          disabled={isBusy}
          className="text-destructive hover:text-destructive"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </Button>
      </div>
    </div>
  );
}
