import { History } from "lucide-react";

import type { WorkflowRun } from "@/features/workflows/api";
import { formatDateTime, runStatusMeta } from "@/features/workflows/format";
import { cn } from "@/lib/utils";

interface WorkflowRunHistoryProps {
  runs: WorkflowRun[];
  isLoading?: boolean;
}

/** Read-only list of a workflow's past executions (newest first). */
export function WorkflowRunHistory({ runs, isLoading }: WorkflowRunHistoryProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="h-12 animate-pulse rounded-md bg-muted" />
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
        const detail = run.error ?? run.result;
        return (
          <li
            key={run.id}
            className="rounded-md border border-border bg-card px-3 py-2"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-medium">
                  {run.trigger === "schedule" ? "Scheduled" : "Manual"} run
                </p>
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
            {detail && (
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                {detail}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
