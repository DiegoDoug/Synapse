import { CheckCheck, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { NotificationList } from "@/features/notifications/components/NotificationList";
import {
  useComposeNotifications,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotificationCounts,
  useNotifications,
} from "@/features/notifications/useNotifications";

/** Notification center — full list with compose, mark-read, and mark-all-read. */
export default function NotificationsPage() {
  const notifications = useNotifications({ limit: 100 });
  const counts = useNotificationCounts();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const compose = useComposeNotifications();

  const unread = counts.data?.unread ?? 0;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
          <p className="text-sm text-muted-foreground">
            {unread > 0
              ? `${unread} unread of ${counts.data?.total ?? 0} total.`
              : "Your reminders and alerts in one place."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={compose.isPending}
            onClick={() => compose.mutate()}
          >
            <RefreshCw className="h-4 w-4" />
            Check for updates
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={unread === 0 || markAllRead.isPending}
            onClick={() => markAllRead.mutate()}
          >
            <CheckCheck className="h-4 w-4" />
            Mark all read
          </Button>
        </div>
      </div>

      <NotificationList
        notifications={notifications.data ?? []}
        isLoading={notifications.isLoading}
        isError={notifications.isError}
        onMarkRead={(id) => markRead.mutate(id)}
        busyId={markRead.isPending ? (markRead.variables as number) : undefined}
        emptyLabel="No notifications yet. Use “Check for updates” to scan your synced data."
      />
    </div>
  );
}
