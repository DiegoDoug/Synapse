import { AgentCard } from "@/features/agents/components/AgentCard";
import { AgentRunView } from "@/features/agents/components/AgentRunView";
import { RunHistory } from "@/features/agents/components/RunHistory";
import { useAgentRuns, useAgents, useStartRun } from "@/features/agents/useAgents";

/** Agents — trigger a domain agent, watch its steps, and review recent runs. */
export default function AgentsPage() {
  const agents = useAgents();
  const runs = useAgentRuns();
  const start = useStartRun();

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
        <p className="text-sm text-muted-foreground">
          Run a domain agent to orchestrate your services into a multi-step
          workflow. Each run records its plan, the tools it used, and the result.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Catalogue + latest run */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold tracking-tight">Available agents</h2>
          {agents.isLoading && (
            <div className="h-40 animate-pulse rounded-lg bg-muted" />
          )}
          {agents.isError && (
            <p className="text-sm text-destructive">Couldn&apos;t load agents.</p>
          )}
          {(agents.data ?? []).map((agent) => (
            <AgentCard
              key={agent.key}
              agent={agent}
              isRunning={start.isPending && start.variables?.agentKey === agent.key}
              onRun={(params) => start.mutate({ agentKey: agent.key, params })}
            />
          ))}

          {start.isError && (
            <p className="text-sm text-destructive">
              The run could not be started. Try again.
            </p>
          )}

          {start.data && (
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="mb-3 text-sm font-semibold tracking-tight">
                Latest run
              </h3>
              <AgentRunView run={start.data} />
            </div>
          )}
        </section>

        {/* Recent runs */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold tracking-tight">Recent runs</h2>
          <RunHistory runs={runs.data ?? []} isLoading={runs.isLoading} />
        </section>
      </div>
    </div>
  );
}
