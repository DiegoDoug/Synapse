/**
 * React Query hooks for the agent layer. Encapsulates query keys and cache
 * invalidation so components stay declarative.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type AgentInfo,
  type AgentRun,
  type AgentRunSummary,
  fetchAgents,
  fetchRun,
  fetchRuns,
  startRun,
} from "@/features/agents/api";

const KEYS = {
  agents: ["agents"] as const,
  runs: ["agents", "runs"] as const,
  run: (id: number) => ["agents", "runs", id] as const,
};

export function useAgents() {
  return useQuery<AgentInfo[]>({
    queryKey: KEYS.agents,
    queryFn: fetchAgents,
  });
}

export function useAgentRuns() {
  return useQuery<AgentRunSummary[]>({
    queryKey: KEYS.runs,
    queryFn: fetchRuns,
  });
}

/** Fetch one run with its full step trail; enabled only when a run is selected. */
export function useAgentRun(runId: number | null) {
  return useQuery<AgentRun>({
    queryKey: KEYS.run(runId ?? 0),
    queryFn: () => fetchRun(runId as number),
    enabled: runId !== null,
  });
}

/** Start an agent run; refreshes the run history on success. */
export function useStartRun() {
  const queryClient = useQueryClient();
  return useMutation<
    AgentRun,
    Error,
    { agentKey: string; params: Record<string, unknown> }
  >({
    mutationFn: ({ agentKey, params }) => startRun(agentKey, params),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEYS.runs }),
  });
}
