import { Activity } from "lucide-react";

import { WidgetCard, WidgetSkeleton } from "@/features/dashboard/components/WidgetCard";

/** Placeholder: recent activity feed. */
export function RecentActivityWidget() {
  return (
    <WidgetCard title="Recent Activity" icon={Activity}>
      <WidgetSkeleton lines={4} />
    </WidgetCard>
  );
}
