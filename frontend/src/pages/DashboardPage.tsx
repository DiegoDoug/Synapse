import { DashboardToolbar } from "@/features/dashboard/components/DashboardToolbar";
import { WidgetGrid } from "@/features/dashboard/components/WidgetGrid";
import { useDashboardStore } from "@/features/dashboard/stores/useDashboardStore";

/** Dashboard route — customizable widget grid with drag, resize, and edit mode. */
export default function DashboardPage() {
  const isEditing = useDashboardStore((state) => state.isEditing);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            {isEditing
              ? "Drag to rearrange, resize from the corner, or remove widgets."
              : "Your Personal OS at a glance."}
          </p>
        </div>
        <DashboardToolbar />
      </div>
      <WidgetGrid />
    </div>
  );
}
