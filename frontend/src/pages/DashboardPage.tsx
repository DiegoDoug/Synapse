import { WidgetGrid } from "@/features/dashboard/components/WidgetGrid";

/** Dashboard route — placeholder widgets in a responsive grid (Stage 1). */
export default function DashboardPage() {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Your Personal OS at a glance.</p>
      </div>
      <WidgetGrid />
    </div>
  );
}
