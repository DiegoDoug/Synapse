/**
 * React Query hooks for the notification center. Encapsulates query keys and
 * cache invalidation so components stay declarative.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  composeNotifications,
  fetchNotificationCounts,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationCounts,
  type NotificationDto,
} from "@/features/notifications/api";

const KEYS = {
  all: ["notifications"] as const,
  list: (unreadOnly: boolean, limit: number) =>
    ["notifications", "list", { unreadOnly, limit }] as const,
  counts: ["notifications", "counts"] as const,
};

interface UseNotificationsOptions {
  unreadOnly?: boolean;
  limit?: number;
}

export function useNotifications(options: UseNotificationsOptions = {}) {
  const { unreadOnly = false, limit = 50 } = options;
  return useQuery<NotificationDto[]>({
    queryKey: KEYS.list(unreadOnly, limit),
    queryFn: () => fetchNotifications({ unreadOnly, limit }),
  });
}

export function useNotificationCounts() {
  return useQuery<NotificationCounts>({
    queryKey: KEYS.counts,
    queryFn: fetchNotificationCounts,
  });
}

/** Invalidate every notification query so lists and the badge refresh together. */
function useInvalidateNotifications() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: KEYS.all });
}

export function useMarkNotificationRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (id: number) => markNotificationRead(id),
    onSuccess: invalidate,
  });
}

export function useMarkAllNotificationsRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
  });
}

export function useComposeNotifications() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: composeNotifications,
    onSuccess: invalidate,
  });
}
