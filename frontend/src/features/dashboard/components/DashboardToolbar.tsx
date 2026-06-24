import { Check, Pencil, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { WidgetLibrary } from "@/features/dashboard/components/WidgetLibrary";
import { useDashboardStore } from "@/features/dashboard/stores/useDashboardStore";

/** Controls for the dashboard: toggle edit mode, add widgets, and reset. */
export function DashboardToolbar() {
  const isEditing = useDashboardStore((state) => state.isEditing);
  const toggleEditing = useDashboardStore((state) => state.toggleEditing);
  const resetDashboard = useDashboardStore((state) => state.resetDashboard);

  return (
    <div className="flex items-center gap-2">
      {isEditing && (
        <>
          <WidgetLibrary />
          <Button variant="outline" size="sm" onClick={resetDashboard}>
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
        </>
      )}
      <Button
        variant={isEditing ? "default" : "outline"}
        size="sm"
        onClick={toggleEditing}
        aria-pressed={isEditing}
      >
        {isEditing ? <Check className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
        {isEditing ? "Done" : "Edit layout"}
      </Button>
    </div>
  );
}
