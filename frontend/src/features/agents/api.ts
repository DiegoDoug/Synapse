/**
 * Agents API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/agent.py. No React/state here.
 */

import { apiGet, apiPost } from "@/api/client";

export interface AgentParam {
  name: string;
  type: string;
  required: boolean;
  description: string | null;
}

export interface AgentInfo {
  key: string;
  name: string;
  description: string;
  parameters: AgentParam[];
}

export type RunStatus = "running" | "completed" | "failed";
export type StepKind = "plan" | "action" | "result" | "error";

export interface AgentStep {
  id: number;
  step_index: number;
  kind: StepKind | string;
  title: string;
  detail: string | null;
  tool_name: string | null;
  status: string;
  created_at: string;
}

export interface AgentRunSummary {
  id: number;
  agent_key: string;
  agent_name: string;
  input: Record<string, unknown>;
  status: RunStatus | string;
  result: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface AgentRun extends AgentRunSummary {
  steps: AgentStep[];
}

export function fetchAgents(): Promise<AgentInfo[]> {
  return apiGet<AgentInfo[]>("/agents");
}

export function fetchRuns(): Promise<AgentRunSummary[]> {
  return apiGet<AgentRunSummary[]>("/agents/runs");
}

export function fetchRun(runId: number): Promise<AgentRun> {
  return apiGet<AgentRun>(`/agents/runs/${runId}`);
}

export function startRun(
  agentKey: string,
  params: Record<string, unknown>,
): Promise<AgentRun> {
  return apiPost<AgentRun>(`/agents/${agentKey}/runs`, { params });
}
