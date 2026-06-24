import { Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useDashboardStore } from "@/features/dashboard/stores/useDashboardStore";
import { WIDGET_DEFINITIONS, WIDGET_ORDER } from "@/features/dashboard/widgetRegistry";

/**
 * Edit-mode popover for adding widgets back to the grid.
 * Lists every registry widget not currently active; removal happens inline
 * on each widget. Open state is local; backdrop closes it on outside click.
 */
export function WidgetLibrary() {
  const [open, setOpen] = useState(false);
  const activeWidgetIds = useDashboardStore((state) => state.activeWidgetIds);
  const addWidget = useDashboardStore((state) => state.addWidget);

  const availableIds = WIDGET_ORDER.filter((id) => !activeWidgetIds.includes(id));

  return (
    <div className="relative">
      <Button variant="outline" size="sm" onClick={() => setOpen((prev) => !prev)}>
        <Plus className="h-4 w-4" />
        Add widget
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden />
          <div className="absolute right-0 z-40 mt-2 w-72 rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md">
            {availableIds.length === 0 ? (
              <p className="px-3 py-4 text-center text-sm text-muted-foreground">
                All widgets are on your dashboard.
              </p>
            ) : (
              availableIds.map((id) => {
                const { title, description, icon: Icon } = WIDGET_DEFINITIONS[id];
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => addWidget(id)}
                    className="flex w-full items-start gap-3 rounded-sm px-3 py-2 text-left transition-colors hover:bg-accent hover:text-accent-foreground"
                  >
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium">{title}</span>
                      <span className="block text-xs text-muted-foreground">{description}</span>
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}
