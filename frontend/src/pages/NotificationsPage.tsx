import { CheckCheck, RefreshCw, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { NotificationList } from "@/features/notifications/components/NotificationList";
import {
  useComposeNotifications,
  useDeliverPending,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotificationCounts,
  useNotifications,
  useSendNotification,
  useTelegramStatus,
} from "@/features/notifications/useNotifications";

/** Notification center — full list with compose, delivery, and read controls. */
export default function NotificationsPage() {
  const notifications = useNotifications({ limit: 100 });
  const counts = useNotificationCounts();
  const telegram = useTelegramStatus();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const compose = useComposeNotifications();
  const send = useSendNotification();
  const deliverPending = useDeliverPending();

  const unread = counts.data?.unread ?? 0;
  const canSend = Boolean(
    telegram.data?.configured && telegram.data?.chat_configured,
  );

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
          {canSend && (
            <Button
              variant="outline"
              size="sm"
              disabled={deliverPending.isPending}
              onClick={() => deliverPending.mutate()}
            >
              <Send className="h-4 w-4" />
              Send pending
            </Button>
          )}
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

      {telegram.data && !canSend && (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          Telegram delivery is not configured. Set <code>TELEGRAM_BOT_TOKEN</code>{" "}
          and <code>TELEGRAM_DEFAULT_CHAT_ID</code> to send notifications to your
          phone.
        </p>
      )}

      <NotificationList
        notifications={notifications.data ?? []}
        isLoading={notifications.isLoading}
        isError={notifications.isError}
        onMarkRead={(id) => markRead.mutate(id)}
        onSend={(id) => send.mutate(id)}
        canSend={canSend}
        busyId={
          markRead.isPending
            ? (markRead.variables as number)
            : send.isPending
              ? (send.variables as number)
              : undefined
        }
        emptyLabel="No notifications yet. Use “Check for updates” to scan your synced data."
      />
    </div>
  );
}
