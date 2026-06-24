import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface WidgetCardProps {
  title: string;
  icon: LucideIcon;
  children: ReactNode;
}

/** Shared shell for dashboard widgets: titled card with an icon. */
export function WidgetCard({ title, icon: Icon, children }: WidgetCardProps) {
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">{children}</CardContent>
    </Card>
  );
}

/** Muted skeleton lines used as placeholder content (no backend yet). */
export function WidgetSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className="h-3 animate-pulse rounded bg-muted"
          style={{ width: `${90 - index * 15}%` }}
        />
      ))}
    </div>
  );
}
