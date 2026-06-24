import { NotificationsWidget } from "@/features/dashboard/components/NotificationsWidget";
import { RecentActivityWidget } from "@/features/dashboard/components/RecentActivityWidget";
import { TodaysOverviewWidget } from "@/features/dashboard/components/TodaysOverviewWidget";
import { UpcomingEventsWidget } from "@/features/dashboard/components/UpcomingEventsWidget";

/** Responsive grid of placeholder dashboard widgets. */
export function WidgetGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <TodaysOverviewWidget />
      <NotificationsWidget />
      <UpcomingEventsWidget />
      <RecentActivityWidget />
    </div>
  );
}
