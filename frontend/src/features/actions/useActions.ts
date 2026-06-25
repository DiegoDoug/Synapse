/**
 * React Query hooks for the confirmation flow. Surfaces the user's pending
 * actions and exposes approve/reject mutations that refresh the list (and the
 * task/conversation views the actions affect) on completion.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveAction,
  fetchPendingActions,
  rejectAction,
  type PendingActionDto,
} from "@/features/actions/api";

export const ACTION_KEYS = {
  all: ["actions"] as const,
  pending: ["actions", "pending"] as const,
};

/** Live list of actions awaiting the user's approval. */
export function usePendingActions() {
  return useQuery<PendingActionDto[]>({
    queryKey: ACTION_KEYS.pending,
    queryFn: () => fetchPendingActions(true),
  });
}

/** Invalidate actions plus the data they mutate, so every view refreshes. */
function useInvalidateAfterResolve() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ACTION_KEYS.all });
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
    queryClient.invalidateQueries({ queryKey: ["ai", "conversation"] });
  };
}

export function useApproveAction() {
  const invalidate = useInvalidateAfterResolve();
  return useMutation({
    mutationFn: (id: number) => approveAction(id),
    onSuccess: invalidate,
  });
}

export function useRejectAction() {
  const invalidate = useInvalidateAfterResolve();
  return useMutation({
    mutationFn: (id: number) => rejectAction(id),
    onSuccess: invalidate,
  });
}
