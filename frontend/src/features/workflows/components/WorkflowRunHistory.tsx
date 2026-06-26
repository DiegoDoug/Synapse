import { History } from "lucide-react";

import type { WorkflowRun, WorkflowRunStep } from "@/features/workflows/api";
import { formatDateTime, runStatusMeta } from "@/features/workflows/format";
import { cn } from "@/lib/utils";

interface WorkflowRunHistoryProps {
  runs: WorkflowRun[];
  isLoading?: boolean;
}

/** Read-only list of a workflow's past executions with their per-step trail. */
export function WorkflowRunHistory({ runs, isLoading }: WorkflowRunHistoryProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="h-16 animate-pulse rounded-md bg-muted" />
        ))}
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
        <History className="h-5 w-5 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No runs yet.</p>
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {runs.map((run) => {
        const status = runStatusMeta(run.status);
        return (
          <li
            key={run.id}
            className="rounded-md border border-border bg-card px-3 py-2"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-medium">{triggerLabel(run.trigger)} run</p>
                <p className="text-xs text-muted-foreground">
                  {formatDateTime(run.created_at)}
                </p>
              </div>
              <span
                className={cn(
                  "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                  status.className,
                )}
              >
                {status.label}
              </span>
            </div>

            {/* Per-step trail (step-visibility) */}
            {run.steps.length > 0 && (
              <ol className="mt-2 space-y-1 border-l border-border pl-3">
                {run.steps.map((step) => (
                  <StepRow key={step.id} step={step} />
                ))}
              </ol>
            )}

            {run.steps.length === 0 && (run.error || run.result) && (
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                {run.error ?? run.result}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function StepRow({ step }: { step: WorkflowRunStep }) {
  const status = runStatusMeta(step.status);
  const detail = step.error ?? step.result;
  return (
    <li>
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-xs">
          <span className="text-muted-foreground">{step.kind}</span>{" "}
          <span className="font-medium">{step.ref}</span>
        </span>
        <span
          className={cn(
            "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
            status.className,
          )}
        >
          {status.label}
        </span>
      </div>
      {detail && (
        <p className="line-clamp-2 text-[11px] text-muted-foreground">{detail}</p>
      )}
    </li>
  );
}

function triggerLabel(trigger: string): string {
  if (trigger === "schedule") return "Scheduled";
  if (trigger === "event") return "Event";
  return "Manual";
}
