/**
 * Workflows API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/workflow.py. No React/state here.
 */

import { apiDelete, apiGet, apiPatch, apiPost } from "@/api/client";

export type ScheduleKind = "manual" | "interval" | "cron" | "event";
export type WorkflowRunStatus = "running" | "completed" | "failed";
export type WorkflowTrigger = "manual" | "schedule" | "event";
export type StepKind = "agent" | "tool";

export interface WorkflowStep {
  step_index: number;
  kind: StepKind;
  ref: string;
  params: Record<string, unknown>;
}

export interface Workflow {
  id: number;
  name: string;
  description: string | null;
  steps: WorkflowStep[];
  schedule_kind: ScheduleKind;
  interval_minutes: number | null;
  cron_hour: number | null;
  cron_minute: number | null;
  event_type: string | null;
  max_runs: number | null;
  enabled: boolean;
  run_count: number;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRunStep {
  id: number;
  step_index: number;
  kind: StepKind | string;
  ref: string;
  status: WorkflowRunStatus | string;
  result: string | null;
  error: string | null;
  agent_run_id: number | null;
}

export interface WorkflowRun {
  id: number;
  workflow_id: number;
  trigger: WorkflowTrigger | string;
  status: WorkflowRunStatus | string;
  result: string | null;
  error: string | null;
  agent_run_id: number | null;
  steps: WorkflowRunStep[];
  created_at: string;
  finished_at: string | null;
}

/** Body for creating/updating a workflow. Update sends only changed fields. */
export interface WorkflowInput {
  name?: string;
  description?: string | null;
  steps?: { kind: StepKind; ref: string; params: Record<string, unknown> }[];
  schedule_kind?: ScheduleKind;
  interval_minutes?: number | null;
  cron_hour?: number | null;
  cron_minute?: number | null;
  event_type?: string | null;
  max_runs?: number | null;
  enabled?: boolean;
}

// --- Catalogue (what the composer can pick from) ---

export interface CatalogueParam {
  name: string;
  description: string | null;
  required: boolean;
}

export interface CatalogueEntry {
  kind: StepKind;
  ref: string;
  name: string;
  description: string;
  parameters: CatalogueParam[];
}

export interface CatalogueEvent {
  event_type: string;
  label: string;
}

export interface WorkflowCatalogue {
  steps: CatalogueEntry[];
  events: CatalogueEvent[];
}

export function fetchCatalogue(): Promise<WorkflowCatalogue> {
  return apiGet<WorkflowCatalogue>("/workflows/catalogue");
}

export function fetchWorkflows(): Promise<Workflow[]> {
  return apiGet<Workflow[]>("/workflows");
}

export function createWorkflow(body: WorkflowInput): Promise<Workflow> {
  return apiPost<Workflow>("/workflows", body);
}

export function updateWorkflow(
  id: number,
  body: WorkflowInput,
): Promise<Workflow> {
  return apiPatch<Workflow>(`/workflows/${id}`, body);
}

export function deleteWorkflow(id: number): Promise<void> {
  return apiDelete(`/workflows/${id}`);
}

export function setWorkflowEnabled(
  id: number,
  enabled: boolean,
): Promise<Workflow> {
  return apiPost<Workflow>(`/workflows/${id}/${enabled ? "enable" : "disable"}`);
}

export function runWorkflow(id: number): Promise<WorkflowRun> {
  return apiPost<WorkflowRun>(`/workflows/${id}/run`);
}

export function fetchWorkflowRuns(id: number): Promise<WorkflowRun[]> {
  return apiGet<WorkflowRun[]>(`/workflows/${id}/runs`);
}
