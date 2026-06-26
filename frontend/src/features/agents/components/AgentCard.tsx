import { useState } from "react";
import { Loader2, Play } from "lucide-react";

import type { AgentInfo } from "@/features/agents/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface AgentCardProps {
  agent: AgentInfo;
  onRun: (params: Record<string, unknown>) => void;
  isRunning: boolean;
}

/** One agent in the catalogue: its description, optional inputs, and a trigger. */
export function AgentCard({ agent, onRun, isRunning }: AgentCardProps) {
  const [values, setValues] = useState<Record<string, string>>({});

  const submit = () => {
    // Drop empty optional params so the backend applies its own defaults.
    const params = Object.fromEntries(
      Object.entries(values).filter(([, v]) => v.trim() !== ""),
    );
    onRun(params);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{agent.name}</CardTitle>
        <CardDescription>{agent.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {agent.parameters.map((param) => (
          <div key={param.name} className="space-y-1">
            <label
              htmlFor={`${agent.key}-${param.name}`}
              className="text-xs font-medium capitalize text-muted-foreground"
            >
              {param.name}
              {param.required && <span className="text-destructive"> *</span>}
            </label>
            <input
              id={`${agent.key}-${param.name}`}
              type="text"
              placeholder={param.description ?? ""}
              value={values[param.name] ?? ""}
              onChange={(e) =>
                setValues((prev) => ({ ...prev, [param.name]: e.target.value }))
              }
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
        ))}
        <Button onClick={submit} disabled={isRunning} className="w-full">
          {isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {isRunning ? "Running…" : "Run agent"}
        </Button>
      </CardContent>
    </Card>
  );
}
