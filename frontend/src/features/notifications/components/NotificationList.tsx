import { BellOff } from "lucide-react";

import type { NotificationDto } from "@/features/notifications/api";
import { NotificationItem } from "@/features/notifications/components/NotificationItem";

interface NotificationListProps {
  notifications: NotificationDto[];
  isLoading?: boolean;
  isError?: boolean;
  onMarkRead?: (id: number) => void;
  busyId?: number;
  /** Message shown when there are no notifications. */
  emptyLabel?: string;
}

/** Renders notifications with loading / error / empty states. */
export function NotificationList({
  notifications,
  isLoading = false,
  isError = false,
  onMarkRead,
  busyId,
  emptyLabel = "You're all caught up.",
}: NotificationListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, index) => (
          <div
            key={index}
            className="h-14 animate-pulse rounded-md bg-muted"
          />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">
        Couldn&apos;t load notifications. Try again.
      </p>
    );
  }

  if (notifications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
        <BellOff className="h-6 w-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">{emptyLabel}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {notifications.map((notification) => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onMarkRead={onMarkRead}
          busy={busyId === notification.id}
        />
      ))}
    </div>
  );
}
