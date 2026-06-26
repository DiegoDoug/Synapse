/**
 * React Query hooks for the automation layer. Encapsulates query keys and
 * cache invalidation so components stay declarative.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type Workflow,
  type WorkflowInput,
  type WorkflowRun,
  createWorkflow,
  deleteWorkflow,
  fetchWorkflowRuns,
  fetchWorkflows,
  runWorkflow,
  setWorkflowEnabled,
  updateWorkflow,
} from "./api";

const KEYS = {
  workflows: ["workflows"] as const,
  runs: (id: number) => ["workflows", id, "runs"] as const,
};

export function useWorkflows() {
  return useQuery<Workflow[]>({
    queryKey: KEYS.workflows,
    queryFn: fetchWorkflows,
  });
}

export function useWorkflowRuns(workflowId: number | null) {
  return useQuery<WorkflowRun[]>({
    queryKey: KEYS.runs(workflowId ?? 0),
    queryFn: () => fetchWorkflowRuns(workflowId as number),
    enabled: workflowId !== null,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation<Workflow, Error, WorkflowInput>({
    mutationFn: createWorkflow,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: KEYS.workflows }),
  });
}

export function useUpdateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation<Workflow, Error, { id: number; input: WorkflowInput }>({
    mutationFn: ({ id, input }) => updateWorkflow(id, input),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: KEYS.workflows }),
  });
}

export function useDeleteWorkflow() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: deleteWorkflow,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: KEYS.workflows }),
  });
}

export function useSetWorkflowEnabled() {
  const queryClient = useQueryClient();
  return useMutation<Workflow, Error, { id: number; enabled: boolean }>({
    mutationFn: ({ id, enabled }) => setWorkflowEnabled(id, enabled),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: KEYS.workflows }),
  });
}

/** Run a workflow now; refreshes both the workflow tally and its run history. */
export function useRunWorkflow() {
  const queryClient = useQueryClient();
  return useMutation<WorkflowRun, Error, number>({
    mutationFn: runWorkflow,
    onSuccess: (_run, workflowId) => {
      queryClient.invalidateQueries({ queryKey: KEYS.workflows });
      queryClient.invalidateQueries({ queryKey: KEYS.runs(workflowId) });
    },
  });
}
