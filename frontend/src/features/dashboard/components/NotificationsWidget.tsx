import { Bell } from "lucide-react";
import { Link } from "react-router-dom";

import { WidgetCard } from "@/features/dashboard/components/WidgetCard";
import { NotificationList } from "@/features/notifications/components/NotificationList";
import {
  useMarkNotificationRead,
  useNotifications,
} from "@/features/notifications/useNotifications";

/** Dashboard widget: the most recent notifications, with a link to the center. */
export function NotificationsWidget() {
  const { data, isLoading, isError } = useNotifications({ limit: 5 });
  const markRead = useMarkNotificationRead();

  return (
    <WidgetCard title="Notifications" icon={Bell}>
      <div className="flex h-full flex-col">
        <div className="flex-1">
          <NotificationList
            notifications={data ?? []}
            isLoading={isLoading}
            isError={isError}
            onMarkRead={(id) => markRead.mutate(id)}
            busyId={markRead.isPending ? (markRead.variables as number) : undefined}
            emptyLabel="No new notifications."
          />
        </div>
        <Link
          to="/notifications"
          className="mt-3 inline-block text-xs font-medium text-primary hover:underline"
        >
          View all notifications →
        </Link>
      </div>
    </WidgetCard>
  );
}
