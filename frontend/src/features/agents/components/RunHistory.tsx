import { History } from "lucide-react";

import type { AgentRunSummary } from "@/features/agents/api";
import { formatDateTime, runStatusMeta } from "@/features/agents/format";
import { cn } from "@/lib/utils";

interface RunHistoryProps {
  runs: AgentRunSummary[];
  isLoading?: boolean;
  selectedId?: number | null;
  onSelect?: (runId: number) => void;
}

/** Compact, selectable list of recent agent runs (newest first). */
export function RunHistory({
  runs,
  isLoading = false,
  selectedId = null,
  onSelect,
}: RunHistoryProps) {
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
        return (
          <li key={run.id}>
            <button
              type="button"
              onClick={() => onSelect?.(run.id)}
              aria-current={selectedId === run.id}
              className={cn(
                "flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2 text-left transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                selectedId === run.id
                  ? "border-primary bg-accent"
                  : "border-border bg-card",
              )}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{run.agent_name}</p>
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
            </button>
          </li>
        );
      })}
    </ul>
  );
}
