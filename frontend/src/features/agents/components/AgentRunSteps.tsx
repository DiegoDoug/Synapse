import type { AgentStep } from "@/features/agents/api";
import { stepIcon } from "@/features/agents/format";
import { cn } from "@/lib/utils";

interface AgentRunStepsProps {
  steps: AgentStep[];
}

/** Renders a run's plan → act → observe trail as a vertical timeline. */
export function AgentRunSteps({ steps }: AgentRunStepsProps) {
  if (steps.length === 0) {
    return <p className="text-sm text-muted-foreground">No steps recorded.</p>;
  }

  return (
    <ol className="space-y-3">
      {steps.map((step) => {
        const Icon = stepIcon(step.kind);
        const failed = step.status === "failed" || step.kind === "error";
        return (
          <li key={step.id} className="flex gap-3">
            <span
              className={cn(
                "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                failed
                  ? "bg-destructive/15 text-destructive"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{step.title}</span>
                {step.tool_name && (
                  <code className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                    {step.tool_name}
                  </code>
                )}
                {failed && (
                  <span className="text-xs font-medium text-destructive">failed</span>
                )}
              </div>
              {step.detail && (
                <pre className="mt-1 whitespace-pre-wrap break-words text-xs text-muted-foreground">
                  {step.detail}
                </pre>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
