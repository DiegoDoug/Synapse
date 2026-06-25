import { BookOpen, Wrench } from "lucide-react";

interface ToolCallChipProps {
  /** Tool name, e.g. "search_emails". */
  name: string;
  /** Short result summary, when available. */
  summary?: string;
}

/** Friendlier labels for tools surfaced as "sources" in the chat. */
const TOOL_LABELS: Record<string, string> = {
  search_knowledge: "Knowledge base",
};

/** Compact indicator that the assistant used a read-only tool (a "source").
 *  Knowledge-base searches render with a book icon so grounded answers visibly
 *  cite where they came from. */
export default function ToolCallChip({ name, summary }: ToolCallChipProps) {
  const isKnowledge = name === "search_knowledge";
  const Icon = isKnowledge ? BookOpen : Wrench;
  const label = TOOL_LABELS[name] ?? name;

  return (
    <div className="flex items-start gap-2 pl-10 text-xs text-muted-foreground">
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        <span className="font-medium text-foreground">{label}</span>
        {summary ? <span className="ml-1">· {summary}</span> : null}
      </span>
    </div>
  );
}
