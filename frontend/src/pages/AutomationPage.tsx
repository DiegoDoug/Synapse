import { useState } from "react";
import { Plus } from "lucide-react";

import { useAgents } from "@/features/agents/useAgents";
import type { Workflow, WorkflowInput } from "@/features/workflows/api";
import { WorkflowCard } from "@/features/workflows/components/WorkflowCard";
import { WorkflowForm } from "@/features/workflows/components/WorkflowForm";
import { WorkflowRunHistory } from "@/features/workflows/components/WorkflowRunHistory";
import {
  useCreateWorkflow,
  useDeleteWorkflow,
  useRunWorkflow,
  useSetWorkflowEnabled,
  useUpdateWorkflow,
  useWorkflowRuns,
  useWorkflows,
} from "@/features/workflows/useWorkflows";
import { Button } from "@/components/ui/button";

type Panel = { mode: "idle" } | { mode: "create" } | { mode: "edit"; workflow: Workflow };

/** Automation — define workflows, personalize their schedule, and review runs. */
export default function AutomationPage() {
  const agents = useAgents();
  const workflows = useWorkflows();

  const create = useCreateWorkflow();
  const update = useUpdateWorkflow();
  const remove = useDeleteWorkflow();
  const toggle = useSetWorkflowEnabled();
  const run = useRunWorkflow();

  const [panel, setPanel] = useState<Panel>({ mode: "idle" });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const runs = useWorkflowRuns(selectedId);

  const busyId = run.isPending ? run.variables : toggle.isPending ? toggle.variables?.id : null;

  const submitCreate = (input: WorkflowInput) =>
    create.mutate(input, { onSuccess: () => setPanel({ mode: "idle" }) });

  const submitEdit = (id: number, input: WorkflowInput) =>
    update.mutate({ id, input }, { onSuccess: () => setPanel({ mode: "idle" }) });

  const onDelete = (workflow: Workflow) => {
    if (!window.confirm(`Delete "${workflow.name}" and its run history?`)) return;
    remove.mutate(workflow.id);
    if (selectedId === workflow.id) setSelectedId(null);
  };

  const agentList = agents.data ?? [];
  const list = workflows.data ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Automation</h1>
          <p className="text-sm text-muted-foreground">
            Run an agent on your own schedule. Choose when and how often it runs
            — and how many times before it stops.
          </p>
        </div>
        <Button
          onClick={() => setPanel({ mode: "create" })}
          disabled={agentList.length === 0}
        >
          <Plus className="h-4 w-4" />
          New workflow
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Workflow list */}
        <section className="space-y-3">
          {workflows.isLoading && (
            <div className="h-32 animate-pulse rounded-lg bg-muted" />
          )}
          {workflows.isError && (
            <p className="text-sm text-destructive">Couldn&apos;t load workflows.</p>
          )}
          {!workflows.isLoading && list.length === 0 && (
            <div className="rounded-lg border border-dashed border-border p-8 text-center">
              <p className="text-sm text-muted-foreground">
                No workflows yet. Create one to automate an agent on a schedule.
              </p>
            </div>
          )}
          {list.map((workflow) => (
            <WorkflowCard
              key={workflow.id}
              workflow={workflow}
              isSelected={selectedId === workflow.id}
              isBusy={busyId === workflow.id}
              onSelect={() => setSelectedId(workflow.id)}
              onRun={() => {
                setSelectedId(workflow.id);
                run.mutate(workflow.id);
              }}
              onToggle={() =>
                toggle.mutate({ id: workflow.id, enabled: !workflow.enabled })
              }
              onEdit={() => setPanel({ mode: "edit", workflow })}
              onDelete={() => onDelete(workflow)}
            />
          ))}
        </section>

        {/* Editor / run history */}
        <section className="space-y-4">
          {panel.mode === "create" && (
            <Card title="New workflow">
              <WorkflowForm
                agents={agentList}
                isSaving={create.isPending}
                error={create.isError ? "Couldn't create the workflow." : null}
                onSubmit={submitCreate}
                onCancel={() => setPanel({ mode: "idle" })}
              />
            </Card>
          )}

          {panel.mode === "edit" && (
            <Card title="Edit workflow">
              <WorkflowForm
                agents={agentList}
                workflow={panel.workflow}
                isSaving={update.isPending}
                error={update.isError ? "Couldn't save the workflow." : null}
                onSubmit={(input) => submitEdit(panel.workflow.id, input)}
                onCancel={() => setPanel({ mode: "idle" })}
              />
            </Card>
          )}

          {panel.mode === "idle" && (
            <Card title="Run history">
              {selectedId === null ? (
                <p className="text-sm text-muted-foreground">
                  Select a workflow to see its past runs.
                </p>
              ) : (
                <WorkflowRunHistory
                  runs={runs.data ?? []}
                  isLoading={runs.isLoading}
                />
              )}
            </Card>
          )}
        </section>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="mb-3 text-sm font-semibold tracking-tight">{title}</h2>
      {children}
    </div>
  );
}
