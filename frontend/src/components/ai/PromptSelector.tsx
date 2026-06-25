import { usePrompts } from "@/features/ai/useAssistant";

interface PromptSelectorProps {
  /** Currently selected system prompt id, or null for the default persona. */
  value: number | null;
  onChange: (value: number | null) => void;
}

/** Dropdown to pick a named system prompt that steers the assistant. */
export default function PromptSelector({ value, onChange }: PromptSelectorProps) {
  const { data: prompts } = usePrompts();

  return (
    <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
      <span>Prompt</span>
      <select
        className="rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={value ?? ""}
        onChange={(event) =>
          onChange(event.target.value ? Number(event.target.value) : null)
        }
      >
        <option value="">Default</option>
        {(prompts ?? []).map((prompt) => (
          <option key={prompt.id} value={prompt.id}>
            {prompt.name}
          </option>
        ))}
      </select>
    </label>
  );
}
