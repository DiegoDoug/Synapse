import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import ChatInput from "@/components/ai/ChatInput";
import ChatMessage from "@/components/ai/ChatMessage";
import ConversationSidebar from "@/components/ai/ConversationSidebar";
import PromptSelector from "@/components/ai/PromptSelector";
import ProviderIndicator from "@/components/ai/ProviderIndicator";
import { type MessageDto } from "@/features/ai/api";
import { useConversation, useSendChat } from "@/features/ai/useAssistant";

/** Optimistic placeholder shown for the user's turn while the reply streams in. */
type PendingMessage = Pick<MessageDto, "role" | "content" | "provider">;

/** Assistant route — chat interface, conversation sidebar, prompt selector. */
export default function AssistantPage() {
  const location = useLocation();
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [promptId, setPromptId] = useState<number | null>(null);
  const [pending, setPending] = useState<PendingMessage | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const conversation = useConversation(conversationId);
  const sendChat = useSendChat();

  const messages = useMemo<PendingMessage[]>(() => {
    const persisted = conversation.data?.messages ?? [];
    return pending ? [...persisted, pending] : persisted;
  }, [conversation.data?.messages, pending]);

  const send = (text: string) => {
    setPending({ role: "user", content: text, provider: null });
    sendChat.mutate(
      {
        message: text,
        conversation_id: conversationId ?? undefined,
        system_prompt_id: promptId ?? undefined,
      },
      {
        onSuccess: (result) => {
          setConversationId(result.conversation_id);
          setPending(null);
        },
        onError: () => setPending(null),
      },
    );
  };

  // "Ask Personal OS" command bar routes here with a prompt to auto-send once.
  const consumedPrompt = useRef<string | null>(null);
  useEffect(() => {
    const prompt = (location.state as { prompt?: string } | null)?.prompt;
    if (prompt && consumedPrompt.current !== prompt) {
      consumedPrompt.current = prompt;
      setConversationId(null);
      send(prompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);

  // Keep the latest message in view.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages.length]);

  const startNewChat = () => {
    setConversationId(null);
    setPending(null);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col gap-4 p-4 md:flex-row md:p-6">
      <aside className="w-full shrink-0 md:w-64">
        <ConversationSidebar
          activeId={conversationId}
          onSelect={setConversationId}
          onNewChat={startNewChat}
        />
      </aside>

      <section className="flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-background">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-2">
          <h1 className="text-sm font-semibold tracking-tight">Assistant</h1>
          <div className="flex items-center gap-3">
            <PromptSelector value={promptId} onChange={setPromptId} />
            <ProviderIndicator />
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
              Ask anything about your day, emails, or schedule.
            </div>
          )}
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}
          {sendChat.isPending && (
            <p className="px-10 text-xs text-muted-foreground">Thinking…</p>
          )}
          {sendChat.isError && (
            <p className="px-10 text-xs text-destructive">
              The assistant is unavailable. Check the provider configuration.
            </p>
          )}
        </div>

        <div className="border-t border-border p-3">
          <ChatInput disabled={sendChat.isPending} onSend={send} />
        </div>
      </section>
    </div>
  );
}
