import { Sparkles } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * "Ask Personal OS" command bar (Stage 4 foundation).
 *
 * For now this only captures free text and routes it to the assistant, which
 * forwards it to the AI service. Future stages turn typed intents ("show
 * today's schedule", "summarize emails") into tool calls; the entry point and
 * routing live here so that wiring has a home.
 */
export default function CommandBar() {
  const [value, setValue] = useState("");
  const navigate = useNavigate();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const text = value.trim();
    if (!text) return;
    navigate("/assistant", { state: { prompt: text } });
    setValue("");
  };

  return (
    <form onSubmit={submit} className="w-full max-w-md">
      <div className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm focus-within:ring-2 focus-within:ring-ring">
        <Sparkles className="h-4 w-4 shrink-0 text-muted-foreground" />
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask Personal OS…"
          aria-label="Ask Personal OS"
          className="w-full bg-transparent text-foreground placeholder:text-muted-foreground focus-visible:outline-none"
        />
      </div>
    </form>
  );
}
