import { useState } from "react";
import { Loader2 } from "lucide-react";

import type { AgentInfo } from "@/features/agents/api";
import type { Workflow, WorkflowInput } from "@/features/workflows/api";
import { ScheduleEditor } from "@/features/workflows/components/ScheduleEditor";
import {
  type ScheduleDraft,
  draftIntervalMinutes,
} from "@/features/workflows/schedule";
import { Button } from "@/components/ui/button";

interface WorkflowFormProps {
  agents: AgentInfo[];
  /** When set, the form edits an existing workflow instead of creating one. */
  workflow?: Workflow;
  isSaving: boolean;
  error?: string | null;
  onSubmit: (input: WorkflowInput) => void;
  onCancel?: () => void;
}

/**
 * Define or edit a workflow: name, which agent runs, its inputs, and the
 * schedule personalization (time / frequency / run cap).
 */
export function WorkflowForm({
  agents,
  workflow,
  isSaving,
  error,
  onSubmit,
  onCancel,
}: WorkflowFormProps) {
  const [name, setName] = useState(workflow?.name ?? "");
  const [description, setDescription] = useState(workflow?.description ?? "");
  const [agentKey, setAgentKey] = useState(
    workflow?.agent_key ?? agents[0]?.key ?? "",
  );
  const [params, setParams] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      Object.entries(workflow?.params ?? {}).map(([k, v]) => [k, String(v)]),
    ),
  );
  const [enabled, setEnabled] = useState(workflow?.enabled ?? false);
  const [schedule, setSchedule] = useState<ScheduleDraft>(() =>
    initialSchedule(workflow),
  );

  const selectedAgent = agents.find((a) => a.key === agentKey);

  const patchSchedule = (patch: Partial<ScheduleDraft>) =>
    setSchedule((prev) => ({ ...prev, ...patch }));

  const submit = () => {
    const input: WorkflowInput = {
      name: name.trim(),
      description: description.trim() || null,
      agent_key: agentKey,
      params: Object.fromEntries(
        Object.entries(params).filter(([, v]) => v.trim() !== ""),
      ),
      schedule_kind: schedule.schedule_kind,
      max_runs:
        schedule.schedule_kind === "manual" || schedule.maxRuns.trim() === ""
          ? null
          : Number(schedule.maxRuns),
      // Manual workflows have no timer; only interval/cron can be enabled.
      enabled: schedule.schedule_kind === "manual" ? false : enabled,
    };

    if (schedule.schedule_kind === "interval") {
      input.interval_minutes = draftIntervalMinutes(schedule);
    } else if (schedule.schedule_kind === "cron") {
      input.cron_hour = schedule.cronHour;
      input.cron_minute = schedule.cronMinute;
    }

    onSubmit(input);
  };

  const canSubmit = name.trim() !== "" && agentKey !== "" && !isSaving;

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

      <Field label="Agent to run" required>
        <select
          value={agentKey}
          onChange={(e) => {
            setAgentKey(e.target.value);
            setParams({});
          }}
          className={inputClass}
        >
          {agents.map((agent) => (
            <option key={agent.key} value={agent.key}>
              {agent.name}
            </option>
          ))}
        </select>
        {selectedAgent && (
          <p className="text-[11px] text-muted-foreground">
            {selectedAgent.description}
          </p>
        )}
      </Field>

      {/* Agent inputs (mirrors the agent's own trigger form). */}
      {selectedAgent?.parameters.map((param) => (
        <Field key={param.name} label={param.name} required={param.required}>
          <input
            type="text"
            value={params[param.name] ?? ""}
            placeholder={param.description ?? ""}
            onChange={(e) =>
              setParams((prev) => ({ ...prev, [param.name]: e.target.value }))
            }
            className={inputClass}
          />
        </Field>
      ))}

      <ScheduleEditor draft={schedule} onChange={patchSchedule} />

      {schedule.schedule_kind !== "manual" && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 rounded border-border"
          />
          Enable schedule now
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

/** Seed the schedule draft from an existing workflow (or sensible defaults). */
function initialSchedule(workflow?: Workflow): ScheduleDraft {
  const base: ScheduleDraft = {
    schedule_kind: workflow?.schedule_kind ?? "manual",
    intervalAmount: 1,
    intervalUnit: "hours",
    cronHour: workflow?.cron_hour ?? 8,
    cronMinute: workflow?.cron_minute ?? 0,
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
