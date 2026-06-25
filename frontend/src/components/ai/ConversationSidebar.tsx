import { MessageSquarePlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useConversations } from "@/features/ai/useAssistant";
import { cn } from "@/lib/utils";

interface ConversationSidebarProps {
  /** Active conversation id, or null for an unsaved new chat. */
  activeId: number | null;
  onSelect: (id: number) => void;
  onNewChat: () => void;
}

/** List of past conversations plus a "new chat" action. */
export default function ConversationSidebar({
  activeId,
  onSelect,
  onNewChat,
}: ConversationSidebarProps) {
  const { data: conversations, isLoading } = useConversations();

  return (
    <div className="flex h-full flex-col gap-3">
      <Button variant="outline" size="sm" onClick={onNewChat} className="w-full">
        <MessageSquarePlus className="h-4 w-4" />
        New chat
      </Button>

      <div className="flex-1 space-y-1 overflow-y-auto">
        {isLoading && (
          <p className="px-2 py-1 text-xs text-muted-foreground">Loading…</p>
        )}
        {!isLoading && (conversations?.length ?? 0) === 0 && (
          <p className="px-2 py-1 text-xs text-muted-foreground">
            No conversations yet.
          </p>
        )}
        {(conversations ?? []).map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            onClick={() => onSelect(conversation.id)}
            className={cn(
              "w-full truncate rounded-md px-3 py-2 text-left text-sm transition-colors",
              "hover:bg-accent hover:text-accent-foreground",
              conversation.id === activeId
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground",
            )}
            title={conversation.title}
          >
            {conversation.title}
          </button>
        ))}
      </div>
    </div>
  );
}
