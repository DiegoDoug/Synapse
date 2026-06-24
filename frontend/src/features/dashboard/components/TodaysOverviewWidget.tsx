import { LayoutGrid } from "lucide-react";

import { WidgetCard } from "@/features/dashboard/components/WidgetCard";

/** Placeholder: high-level summary of the day. */
export function TodaysOverviewWidget() {
  return (
    <WidgetCard title="Today's Overview" icon={LayoutGrid}>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-2xl font-semibold">—</p>
          <p className="text-xs text-muted-foreground">Tasks</p>
        </div>
        <div>
          <p className="text-2xl font-semibold">—</p>
          <p className="text-xs text-muted-foreground">Events</p>
        </div>
      </div>
    </WidgetCard>
  );
}
