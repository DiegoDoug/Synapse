import type { AgentRun } from "@/features/agents/api";
import { AgentRunSteps } from "@/features/agents/components/AgentRunSteps";
import { formatDateTime, runStatusMeta } from "@/features/agents/format";
import { cn } from "@/lib/utils";

interface AgentRunViewProps {
  run: AgentRun;
}

/** A single run: header (agent + status), its steps, and the final result. */
export function AgentRunView({ run }: AgentRunViewProps) {
  const status = runStatusMeta(run.status);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold">{run.agent_name}</span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            status.className,
          )}
        >
          {status.label}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatDateTime(run.created_at)}
        </span>
      </div>

      <AgentRunSteps steps={run.steps} />

      {run.error && (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {run.error}
        </p>
      )}
    </div>
  );
}
