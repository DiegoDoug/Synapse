import { Bot, User } from "lucide-react";

import { type MessageDto } from "@/features/ai/api";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  message: Pick<MessageDto, "role" | "content" | "provider">;
}

/** A single chat bubble — user right-aligned, assistant left with provider tag. */
export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const Icon = isUser ? User : Bot;

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-card text-muted-foreground">
        <Icon className="h-4 w-4" />
      </span>
      <div className={cn("max-w-[80%] space-y-1", isUser && "text-right")}>
        <div
          className={cn(
            "inline-block whitespace-pre-wrap rounded-lg px-3 py-2 text-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : "border border-border bg-card text-card-foreground",
          )}
        >
          {message.content}
        </div>
        {!isUser && message.provider && (
          <p className="text-xs text-muted-foreground capitalize">
            {message.provider}
          </p>
        )}
      </div>
    </div>
  );
}
