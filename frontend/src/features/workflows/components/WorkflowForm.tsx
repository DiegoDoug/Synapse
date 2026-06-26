import { useState } from "react";
import { Loader2 } from "lucide-react";

import type {
  Workflow,
  WorkflowCatalogue,
  WorkflowInput,
} from "@/features/workflows/api";
import { ScheduleEditor } from "@/features/workflows/components/ScheduleEditor";
import {
  type StepDraft,
  StepEditor,
} from "@/features/workflows/components/StepEditor";
import {
  type ScheduleDraft,
  draftIntervalMinutes,
} from "@/features/workflows/schedule";
import { Button } from "@/components/ui/button";

interface WorkflowFormProps {
  catalogue: WorkflowCatalogue;
  /** When set, the form edits an existing workflow instead of creating one. */
  workflow?: Workflow;
  isSaving: boolean;
  error?: string | null;
  onSubmit: (input: WorkflowInput) => void;
  onCancel?: () => void;
}

/**
 * Define or edit a workflow: name, the composed step sequence, and the
 * schedule/trigger personalization (time / frequency / event / run cap).
 */
export function WorkflowForm({
  catalogue,
  workflow,
  isSaving,
  error,
  onSubmit,
  onCancel,
}: WorkflowFormProps) {
  const [name, setName] = useState(workflow?.name ?? "");
  const [description, setDescription] = useState(workflow?.description ?? "");
  const [steps, setSteps] = useState<StepDraft[]>(() =>
    initialSteps(workflow, catalogue),
  );
  const [enabled, setEnabled] = useState(workflow?.enabled ?? false);
  const [schedule, setSchedule] = useState<ScheduleDraft>(() =>
    initialSchedule(workflow, catalogue),
  );

  const patchSchedule = (patch: Partial<ScheduleDraft>) =>
    setSchedule((prev) => ({ ...prev, ...patch }));

  const submit = () => {
    const isManual = schedule.schedule_kind === "manual";
    const input: WorkflowInput = {
      name: name.trim(),
      description: description.trim() || null,
      steps: steps.map((s) => ({
        kind: s.kind,
        ref: s.ref,
        // Drop empty inputs so the backend / agent applies its own defaults.
        params: Object.fromEntries(
          Object.entries(s.params).filter(([, v]) => v.trim() !== ""),
        ),
      })),
      schedule_kind: schedule.schedule_kind,
      max_runs:
        isManual || schedule.maxRuns.trim() === ""
          ? null
          : Number(schedule.maxRuns),
      // Manual workflows have no timer; only timed/event triggers can be enabled.
      enabled: isManual ? false : enabled,
    };

    if (schedule.schedule_kind === "interval") {
      input.interval_minutes = draftIntervalMinutes(schedule);
    } else if (schedule.schedule_kind === "cron") {
      input.cron_hour = schedule.cronHour;
      input.cron_minute = schedule.cronMinute;
    } else if (schedule.schedule_kind === "event") {
      input.event_type = schedule.eventType || null;
    }

    onSubmit(input);
  };

  const canSubmit = name.trim() !== "" && steps.length > 0 && !isSaving;

  return (
    <div className="space-y-4">
      <Field label="Name" required>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Morning inbox triage"
          className={inputClass}
        />
      </Field>

      <Field label="Description">
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional — what this automation does"
          className={inputClass}
        />
      </Field>

      <StepEditor
        catalogue={catalogue.steps}
        steps={steps}
        onChange={setSteps}
      />

      <ScheduleEditor
        draft={schedule}
        events={catalogue.events}
        onChange={patchSchedule}
      />

      {schedule.schedule_kind !== "manual" && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 rounded border-border"
          />
          Enable this trigger now
        </label>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex gap-2">
        <Button onClick={submit} disabled={!canSubmit}>
          {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
          {workflow ? "Save changes" : "Create workflow"}
        </Button>
        {onCancel && (
          <Button variant="outline" onClick={onCancel} disabled={isSaving}>
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}

const inputClass =
  "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium capitalize text-muted-foreground">
        {label}
        {required && <span className="text-destructive"> *</span>}
      </label>
      {children}
    </div>
  );
}

/** Seed the step sequence from an existing workflow (or one default step). */
function initialSteps(
  workflow: Workflow | undefined,
  catalogue: WorkflowCatalogue,
): StepDraft[] {
  if (workflow && workflow.steps.length > 0) {
    return workflow.steps.map((s) => ({
      kind: (s.kind as "agent" | "tool") ?? "agent",
      ref: s.ref,
      params: Object.fromEntries(
        Object.entries(s.params ?? {}).map(([k, v]) => [k, String(v)]),
      ),
    }));
  }
  const first = catalogue.steps[0];
  return first ? [{ kind: first.kind, ref: first.ref, params: {} }] : [];
}

/** Seed the schedule draft from an existing workflow (or sensible defaults). */
function initialSchedule(
  workflow: Workflow | undefined,
  catalogue: WorkflowCatalogue,
): ScheduleDraft {
  const base: ScheduleDraft = {
    schedule_kind: workflow?.schedule_kind ?? "manual",
    intervalAmount: 1,
    intervalUnit: "hours",
    cronHour: workflow?.cron_hour ?? 8,
    cronMinute: workflow?.cron_minute ?? 0,
    eventType:
      workflow?.event_type ?? catalogue.events[0]?.event_type ?? "",
    maxRuns: workflow?.max_runs != null ? String(workflow.max_runs) : "",
  };
  const minutes = workflow?.interval_minutes;
  if (minutes != null) {
    if (minutes % 1440 === 0) {
      base.intervalAmount = minutes / 1440;
      base.intervalUnit = "days";
    } else if (minutes % 60 === 0) {
      base.intervalAmount = minutes / 60;
      base.intervalUnit = "hours";
    } else {
      base.intervalAmount = minutes;
      base.intervalUnit = "minutes";
    }
  }
  return base;
}
