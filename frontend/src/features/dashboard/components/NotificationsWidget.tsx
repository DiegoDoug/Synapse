import { Bell } from "lucide-react";

import { WidgetCard } from "@/features/dashboard/components/WidgetCard";

/** Placeholder: recent notifications. */
export function NotificationsWidget() {
  return (
    <WidgetCard title="Notifications" icon={Bell}>
      <p className="text-sm text-muted-foreground">No new notifications.</p>
    </WidgetCard>
  );
}
