/**
 * Pending-action API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/action.py. No React/state here.
 */

import { apiGet, apiPost } from "@/api/client";

export type ActionStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "executed"
  | "failed";

export interface PendingActionDto {
  id: number;
  conversation_id: number | null;
  tool_name: string;
  action_type: string;
  summary: string;
  payload: Record<string, unknown>;
  status: ActionStatus | string;
  result: string | null;
  created_at: string;
  resolved_at: string | null;
}

export function fetchPendingActions(pendingOnly = true): Promise<PendingActionDto[]> {
  return apiGet<PendingActionDto[]>(`/actions?pending_only=${pendingOnly}`);
}

export function approveAction(id: number): Promise<PendingActionDto> {
  return apiPost<PendingActionDto>(`/actions/${id}/approve`);
}

export function rejectAction(id: number): Promise<PendingActionDto> {
  return apiPost<PendingActionDto>(`/actions/${id}/reject`);
}
