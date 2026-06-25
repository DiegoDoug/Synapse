import { Wrench } from "lucide-react";

interface ToolCallChipProps {
  /** Tool name, e.g. "search_emails". */
  name: string;
  /** Short result summary, when available. */
  summary?: string;
}

/** Compact indicator that the assistant used a read-only tool (a "source"). */
export default function ToolCallChip({ name, summary }: ToolCallChipProps) {
  return (
    <div className="flex items-start gap-2 pl-10 text-xs text-muted-foreground">
      <Wrench className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        <span className="font-medium text-foreground">{name}</span>
        {summary ? <span className="ml-1">· {summary}</span> : null}
      </span>
    </div>
  );
}
