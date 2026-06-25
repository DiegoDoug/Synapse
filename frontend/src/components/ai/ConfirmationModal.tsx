import { AlertTriangle, Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { type PendingActionDto } from "@/features/actions/api";

interface ConfirmationModalProps {
  /** Actions awaiting approval; the modal shows nothing when empty. */
  actions: PendingActionDto[];
  /** Approve (and execute) one action by id. */
  onApprove: (id: number) => void;
  /** Reject one action by id. */
  onReject: (id: number) => void;
  /** Ids currently being approved/rejected (buttons disable + show busy). */
  busyId?: number | null;
}

/** Human label for an action's change kind. */
const ACTION_LABEL: Record<string, string> = {
  update: "Update",
  delete: "Delete",
  create: "Create",
};

/**
 * Modal that surfaces assistant-proposed writes (updates / deletes / widget
 * config changes) for the user to approve or reject before they execute. One
 * card per pending action; the modal hides itself when the queue is empty.
 */
export default function ConfirmationModal({
  actions,
  onApprove,
  onReject,
  busyId,
}: ConfirmationModalProps) {
  if (actions.length === 0) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg border border-border bg-background shadow-lg">
        <header className="flex items-center gap-2 border-b border-border px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <h2 className="text-sm font-semibold">
            {actions.length === 1
              ? "Confirm action"
              : `Confirm actions (${actions.length})`}
          </h2>
        </header>

        <div className="max-h-[60vh] space-y-3 overflow-y-auto p-4">
          {actions.map((action) => {
            const busy = busyId === action.id;
            return (
              <div
                key={action.id}
                className="rounded-md border border-border p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium">{action.summary}</p>
                  <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    {ACTION_LABEL[action.action_type] ?? action.action_type}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  The assistant wants to run{" "}
                  <span className="font-mono">{action.tool_name}</span>. This
                  will only take effect if you approve it.
                </p>

                <div className="mt-3 flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busy}
                    onClick={() => onReject(action.id)}
                  >
                    <X className="h-3.5 w-3.5" />
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    disabled={busy}
                    onClick={() => onApprove(action.id)}
                  >
                    <Check className="h-3.5 w-3.5" />
                    {busy ? "Working…" : "Approve"}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
