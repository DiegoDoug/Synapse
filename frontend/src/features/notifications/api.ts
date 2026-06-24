/**
 * Notification center API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/notification.py. No React/state here.
 */

import { apiGet, apiPost } from "@/api/client";

export type NotificationCategory =
  | "summary"
  | "reminder"
  | "alert"
  | "manual";

export interface NotificationDto {
  id: number;
  category: NotificationCategory | string;
  priority: "low" | "normal" | "high" | string;
  title: string;
  body: string | null;
  source: string | null;
  is_read: boolean;
  read_at: string | null;
  is_delivered: boolean;
  delivered_at: string | null;
  created_at: string;
}

export interface NotificationCounts {
  unread: number;
  total: number;
}

export interface TelegramStatus {
  configured: boolean;
  chat_configured: boolean;
}

export interface DeliveryResult {
  configured: boolean;
  delivered: number;
  skipped: number;
}

export interface ComposeResult {
  created: number;
  notifications: NotificationDto[];
}

export interface MarkAllReadResult {
  updated: number;
}

interface ListParams {
  limit?: number;
  offset?: number;
  unreadOnly?: boolean;
}

export function fetchNotifications(
  params: ListParams = {},
): Promise<NotificationDto[]> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  if (params.unreadOnly) query.set("unread_only", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiGet<NotificationDto[]>(`/notifications${suffix}`);
}

export function fetchNotificationCounts(): Promise<NotificationCounts> {
  return apiGet<NotificationCounts>("/notifications/counts");
}

export function markNotificationRead(id: number): Promise<NotificationDto> {
  return apiPost<NotificationDto>(`/notifications/${id}/read`);
}

export function markAllNotificationsRead(): Promise<MarkAllReadResult> {
  return apiPost<MarkAllReadResult>("/notifications/read-all");
}

export function composeNotifications(): Promise<ComposeResult> {
  return apiPost<ComposeResult>("/notifications/compose");
}

export function fetchTelegramStatus(): Promise<TelegramStatus> {
  return apiGet<TelegramStatus>("/notifications/telegram");
}

export function sendNotification(id: number): Promise<DeliveryResult> {
  return apiPost<DeliveryResult>(`/notifications/${id}/send`);
}

export function deliverPendingNotifications(): Promise<DeliveryResult> {
  return apiPost<DeliveryResult>("/notifications/deliver");
}
