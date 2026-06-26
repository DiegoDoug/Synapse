/**
 * ScheduleEditor — the personalization surface for *when and how often* a
 * workflow runs. Three modes:
 *
 * - Manual   → no timer; the workflow only runs when triggered.
 * - Interval → repeat every N minutes/hours/days (the frequency).
 * - Daily    → run once a day at a chosen time (UTC).
 *
 * Plus an optional cap on *how many times* it may run before auto-disabling.
 * Emits a normalized patch the form folds into its draft.
 */

import type { ScheduleKind } from "@/features/workflows/api";
import {
  type IntervalUnit,
  type ScheduleDraft,
} from "@/features/workflows/schedule";
import { cn } from "@/lib/utils";

const MODES: { kind: ScheduleKind; label: string; hint: string }[] = [
  { kind: "manual", label: "On demand", hint: "Run only when you click" },
  { kind: "interval", label: "Repeating", hint: "Every N minutes/hours" },
  { kind: "cron", label: "Daily", hint: "Once a day at a set time" },
];

interface ScheduleEditorProps {
  draft: ScheduleDraft;
  onChange: (patch: Partial<ScheduleDraft>) => void;
}

export function ScheduleEditor({ draft, onChange }: ScheduleEditorProps) {
  return (
    <div className="space-y-3">
      <label className="text-xs font-medium text-muted-foreground">
        Schedule
      </label>

      {/* Mode picker */}
      <div className="grid grid-cols-3 gap-2">
        {MODES.map((mode) => (
          <button
            key={mode.kind}
            type="button"
            onClick={() => onChange({ schedule_kind: mode.kind })}
            className={cn(
              "rounded-md border px-2 py-2 text-left transition-colors",
              draft.schedule_kind === mode.kind
                ? "border-primary bg-accent"
                : "border-border bg-background hover:bg-accent",
            )}
          >
            <span className="block text-sm font-medium">{mode.label}</span>
            <span className="block text-[11px] text-muted-foreground">
              {mode.hint}
            </span>
          </button>
        ))}
      </div>

      {/* Interval frequency — how often */}
      {draft.schedule_kind === "interval" && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Every</span>
          <input
            type="number"
            min={1}
            value={draft.intervalAmount}
            onChange={(e) =>
              onChange({ intervalAmount: Number(e.target.value) })
            }
            className="w-20 rounded-md border border-border bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <select
            value={draft.intervalUnit}
            onChange={(e) =>
              onChange({ intervalUnit: e.target.value as IntervalUnit })
            }
            className="rounded-md border border-border bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="minutes">minutes</option>
            <option value="hours">hours</option>
            <option value="days">days</option>
          </select>
        </div>
      )}

      {/* Daily time — when */}
      {draft.schedule_kind === "cron" && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">At</span>
          <input
            type="time"
            value={`${pad(draft.cronHour)}:${pad(draft.cronMinute)}`}
            onChange={(e) => {
              const [h, m] = e.target.value.split(":").map(Number);
              onChange({ cronHour: h || 0, cronMinute: m || 0 });
            }}
            className="rounded-md border border-border bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <span className="text-xs text-muted-foreground">UTC</span>
        </div>
      )}

      {/* Run cap — how many times */}
      {draft.schedule_kind !== "manual" && (
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">
            Stop after (leave blank for unlimited)
          </label>
          <input
            type="number"
            min={1}
            placeholder="Unlimited"
            value={draft.maxRuns}
            onChange={(e) => onChange({ maxRuns: e.target.value })}
            className="w-40 rounded-md border border-border bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <p className="text-[11px] text-muted-foreground">
            How many times the automation may run before it turns itself off.
          </p>
        </div>
      )}
    </div>
  );
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}
