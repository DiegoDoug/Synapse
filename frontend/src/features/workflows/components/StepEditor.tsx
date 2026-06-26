/**
 * StepEditor — the workflow composer. Builds an ordered sequence of steps,
 * each running an agent or a tool from the catalogue with its own inputs. Steps
 * can be added, removed, and reordered; the picked entry's parameters render as
 * inputs so the user supplies what the agent/tool needs.
 */

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";

import type { CatalogueEntry } from "@/features/workflows/api";
import { Button } from "@/components/ui/button";

/** One composed step in the form's working state. */
export interface StepDraft {
  kind: "agent" | "tool";
  ref: string;
  params: Record<string, string>;
}

interface StepEditorProps {
  catalogue: CatalogueEntry[];
  steps: StepDraft[];
  onChange: (steps: StepDraft[]) => void;
}

export function StepEditor({ catalogue, steps, onChange }: StepEditorProps) {
  const agents = catalogue.filter((e) => e.kind === "agent");
  const tools = catalogue.filter((e) => e.kind === "tool");

  const entryOf = (step: StepDraft) =>
    catalogue.find((e) => e.kind === step.kind && e.ref === step.ref);

  const update = (index: number, next: StepDraft) =>
    onChange(steps.map((s, i) => (i === index ? next : s)));

  const select = (index: number, value: string) => {
    const [kind, ref] = value.split(":") as ["agent" | "tool", string];
    update(index, { kind, ref, params: {} });
  };

  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  const add = () => {
    const first = catalogue[0];
    if (!first) return;
    onChange([...steps, { kind: first.kind, ref: first.ref, params: {} }]);
  };

  return (
    <div className="space-y-3">
      <label className="text-xs font-medium text-muted-foreground">
        Steps — run in order
      </label>

      {steps.length === 0 && (
        <p className="rounded-md border border-dashed border-border px-3 py-3 text-xs text-muted-foreground">
          Add at least one step. Each runs an agent or a tool in sequence.
        </p>
      )}

      {steps.map((step, index) => {
        const entry = entryOf(step);
        return (
          <div key={index} className="rounded-md border border-border bg-background p-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-muted-foreground">
                {index + 1}.
              </span>
              <select
                value={`${step.kind}:${step.ref}`}
                onChange={(e) => select(index, e.target.value)}
                className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <optgroup label="Agents">
                  {agents.map((e) => (
                    <option key={e.ref} value={`agent:${e.ref}`}>
                      {e.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Tools">
                  {tools.map((e) => (
                    <option key={e.ref} value={`tool:${e.ref}`}>
                      {e.name}
                    </option>
                  ))}
                </optgroup>
              </select>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => move(index, -1)}
                disabled={index === 0}
                aria-label="Move step up"
              >
                <ArrowUp className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => move(index, 1)}
                disabled={index === steps.length - 1}
                aria-label="Move step down"
              >
                <ArrowDown className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => onChange(steps.filter((_, i) => i !== index))}
                aria-label="Remove step"
                className="text-destructive hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>

            {entry?.description && (
              <p className="mt-1 pl-5 text-[11px] text-muted-foreground">
                {entry.description}
              </p>
            )}

            {/* Inputs for the picked agent/tool */}
            {entry?.parameters.map((param) => (
              <div key={param.name} className="mt-2 space-y-1 pl-5">
                <label className="text-[11px] font-medium capitalize text-muted-foreground">
                  {param.name}
                  {param.required && <span className="text-destructive"> *</span>}
                </label>
                <input
                  type="text"
                  value={step.params[param.name] ?? ""}
                  placeholder={param.description ?? ""}
                  onChange={(e) =>
                    update(index, {
                      ...step,
                      params: { ...step.params, [param.name]: e.target.value },
                    })
                  }
                  className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
            ))}
          </div>
        );
      })}

      <Button
        size="sm"
        variant="outline"
        onClick={add}
        disabled={catalogue.length === 0}
      >
        <Plus className="h-3.5 w-3.5" />
        Add step
      </Button>
    </div>
  );
}
