import { Send } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useState } from "react";

import { Button } from "@/components/ui/button";

interface ChatInputProps {
  disabled?: boolean;
  onSend: (message: string) => void;
}

/** Auto-clearing message composer. Enter sends; Shift+Enter inserts a newline. */
export default function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        placeholder="Message the assistant…"
        className="max-h-40 min-h-[40px] flex-1 resize-y rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
      <Button type="submit" size="icon" disabled={disabled || !value.trim()}>
        <Send className="h-4 w-4" />
      </Button>
    </form>
  );
}
