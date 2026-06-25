import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import ChatInput from "@/components/ai/ChatInput";
import ChatMessage from "@/components/ai/ChatMessage";
import ConfirmationModal from "@/components/ai/ConfirmationModal";
import ConversationSidebar from "@/components/ai/ConversationSidebar";
import PromptSelector from "@/components/ai/PromptSelector";
import ProviderIndicator from "@/components/ai/ProviderIndicator";
import ToolCallChip from "@/components/ai/ToolCallChip";
import VoiceButton from "@/components/ai/VoiceButton";
import {
  useApproveAction,
  usePendingActions,
  useRejectAction,
} from "@/features/actions/useActions";
import { type MessageDto } from "@/features/ai/api";
import { useConversation, useStreamChat } from "@/features/ai/useAssistant";
import { useVoice, useVoiceConfig } from "@/features/voice/useVoice";
import { useWakeWord } from "@/features/voice/useWakeWord";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";

/** Split a persisted tool row ("name: summary") into its parts for a chip. */
function parseToolRow(content: string): { name: string; summary?: string } {
  const idx = content.indexOf(":");
  if (idx === -1) return { name: content };
  return { name: content.slice(0, idx).trim(), summary: content.slice(idx + 1).trim() };
}

/** Assistant route — streaming chat, conversation sidebar, prompt selector. */
export default function AssistantPage() {
  const location = useLocation();
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [promptId, setPromptId] = useState<number | null>(null);
  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const conversation = useConversation(conversationId);
  const stream = useStreamChat();

  // Voice (Stage 4.7): push-to-talk input + optional read-back of replies.
  const voiceConfig = useVoiceConfig();
  const voice = useVoice();
  const voiceAutoRead = useAppStore((state) => state.voiceAutoRead);
  const sttAvailable = voiceConfig.data?.stt_available ?? false;
  const ttsAvailable = voiceConfig.data?.tts_available ?? false;
  // Last assistant message already spoken, so auto-read fires once per reply
  // and never re-reads history when a conversation is opened.
  const lastReadIdRef = useRef<number | null>(null);

  // Writes the assistant proposed (updates / deletes / widget config) await the
  // user's approval here before they run.
  const pendingActions = usePendingActions();
  const approve = useApproveAction();
  const reject = useRejectAction();
  const resolvingId = approve.isPending
    ? approve.variables ?? null
    : reject.isPending
      ? reject.variables ?? null
      : null;

  const persisted = useMemo<MessageDto[]>(
    () => conversation.data?.messages ?? [],
    [conversation.data],
  );

  const send = (text: string) => {
    setPendingUser(text);
    void stream.send(
      {
        message: text,
        conversation_id: conversationId ?? undefined,
        system_prompt_id: promptId ?? undefined,
      },
      (id) => setConversationId(id),
    );
  };

  // Wake-word mode (opt-in): a recognized utterance is injected as a normal
  // message, reusing the same chat path as typing or push-to-talk.
  const wakeWordEnabled = useAppStore((state) => state.voiceWakeWord);
  const wakeAvailable = voiceConfig.data?.wake_word_available ?? false;
  const wake = useWakeWord((text) => send(text));
  const wakeActive = wakeWordEnabled && wakeAvailable;
  useEffect(() => {
    if (wakeActive) void wake.start();
    else wake.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wakeActive]);

  // Clear the optimistic overlay once streaming settles (persisted history,
  // refetched on completion, takes over rendering).
  useEffect(() => {
    if (!stream.isStreaming && pendingUser !== null) {
      setPendingUser(null);
      stream.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.isStreaming]);

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

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [persisted.length, stream.draft, stream.toolCalls.length]);

  // Reset the auto-read marker when switching threads so opening a conversation
  // never reads its existing history aloud.
  useEffect(() => {
    lastReadIdRef.current = null;
  }, [conversationId]);

  // Auto-read: speak each newly arrived assistant reply once, when enabled.
  useEffect(() => {
    const lastAssistant = [...persisted]
      .reverse()
      .find((m) => m.role === "assistant");
    if (!lastAssistant) return;
    if (lastReadIdRef.current === null) {
      // First load of this thread — adopt the latest id without speaking.
      lastReadIdRef.current = lastAssistant.id;
      return;
    }
    if (
      lastAssistant.id > lastReadIdRef.current &&
      voiceAutoRead &&
      ttsAvailable
    ) {
      lastReadIdRef.current = lastAssistant.id;
      void voice.speak(lastAssistant.content);
    }
  }, [persisted, voiceAutoRead, ttsAvailable, voice]);

  const startNewChat = () => {
    setConversationId(null);
    setPendingUser(null);
    stream.reset();
  };

  const overlayActive = pendingUser !== null;
  const isEmpty = persisted.length === 0 && !overlayActive;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col gap-4 p-4 md:flex-row md:p-6">
      <aside className="w-full shrink-0 md:w-64">
        <ConversationSidebar
          activeId={conversationId}
          onSelect={(id) => {
            setConversationId(id);
            setPendingUser(null);
          }}
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
          {isEmpty && (
            <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
              Ask anything about your day, emails, or schedule.
            </div>
          )}

          {persisted.map((message) =>
            message.role === "tool" ? (
              <ToolCallChip key={message.id} {...parseToolRow(message.content)} />
            ) : (
              <ChatMessage key={message.id} message={message} />
            ),
          )}

          {/* Live overlay for the in-flight turn. */}
          {overlayActive && (
            <>
              <ChatMessage
                message={{ role: "user", content: pendingUser, provider: null }}
              />
              {stream.toolCalls.map((tool, index) => (
                <ToolCallChip
                  key={`live-${index}`}
                  name={tool.name}
                  summary={tool.summary}
                />
              ))}
              {stream.draft && (
                <ChatMessage
                  message={{ role: "assistant", content: stream.draft, provider: null }}
                />
              )}
              {stream.isStreaming && !stream.draft && (
                <p className="px-10 text-xs text-muted-foreground">Thinking…</p>
              )}
            </>
          )}

          {stream.error && (
            <p className="px-10 text-xs text-destructive">{stream.error}</p>
          )}
        </div>

        {wakeActive && (
          <div className="flex items-center gap-2 border-t border-border px-4 py-1.5 text-xs text-muted-foreground">
            <span
              className={cn(
                "inline-block h-2 w-2 rounded-full",
                wake.status === "recording"
                  ? "animate-pulse bg-red-500"
                  : wake.status === "armed"
                    ? "bg-emerald-500"
                    : "bg-muted-foreground/40",
              )}
            />
            {wake.status === "recording"
              ? "Listening…"
              : wake.status === "armed"
                ? "Waiting for the wake word"
                : wake.error
                  ? wake.error
                  : "Connecting…"}
          </div>
        )}

        <div className="flex items-end gap-2 border-t border-border p-3">
          {sttAvailable && (
            <VoiceButton
              disabled={stream.isStreaming}
              onTranscript={(text) => send(text)}
            />
          )}
          <div className="flex-1">
            <ChatInput disabled={stream.isStreaming} onSend={send} />
          </div>
        </div>
      </section>

      <ConfirmationModal
        actions={pendingActions.data ?? []}
        onApprove={(id) => approve.mutate(id)}
        onReject={(id) => reject.mutate(id)}
        busyId={resolvingId}
      />
    </div>
  );
}
