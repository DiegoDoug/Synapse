import { Calendar } from "lucide-react";

import { WidgetCard, WidgetSkeleton } from "@/features/dashboard/components/WidgetCard";

/** Placeholder: upcoming calendar events. */
export function UpcomingEventsWidget() {
  return (
    <WidgetCard title="Upcoming Events" icon={Calendar}>
      <WidgetSkeleton lines={3} />
    </WidgetCard>
  );
}
