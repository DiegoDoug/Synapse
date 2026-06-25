/**
 * React Query hooks for the AI assistant. Encapsulates query keys and cache
 * invalidation so components stay declarative.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import {
  type AIHealthDto,
  type ChatRequestBody,
  type ChatResultDto,
  type ConversationDetailDto,
  type ConversationDto,
  type SystemPromptDto,
  type ToolCallEvent,
  fetchAIHealth,
  fetchConversation,
  fetchConversations,
  fetchPrompts,
  sendChat,
  streamChat,
} from "@/features/ai/api";

const KEYS = {
  all: ["ai"] as const,
  health: ["ai", "health"] as const,
  prompts: ["ai", "prompts"] as const,
  conversations: ["ai", "conversations"] as const,
  conversation: (id: number) => ["ai", "conversation", id] as const,
};

export function useAIHealth() {
  return useQuery<AIHealthDto>({
    queryKey: KEYS.health,
    queryFn: fetchAIHealth,
  });
}

export function usePrompts() {
  return useQuery<SystemPromptDto[]>({
    queryKey: KEYS.prompts,
    queryFn: fetchPrompts,
  });
}

export function useConversations() {
  return useQuery<ConversationDto[]>({
    queryKey: KEYS.conversations,
    queryFn: fetchConversations,
  });
}

/** Load a single conversation with its messages; disabled until an id exists. */
export function useConversation(id: number | null) {
  return useQuery<ConversationDetailDto>({
    queryKey: KEYS.conversation(id ?? 0),
    queryFn: () => fetchConversation(id as number),
    enabled: id !== null,
  });
}

/** Send a chat message and refresh the affected conversation + list. */
export function useSendChat() {
  const queryClient = useQueryClient();
  return useMutation<ChatResultDto, Error, ChatRequestBody>({
    mutationFn: sendChat,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: KEYS.conversations });
      queryClient.invalidateQueries({
        queryKey: KEYS.conversation(result.conversation_id),
      });
    },
  });
}

interface StreamState {
  /** Assistant text accumulated so far this turn. */
  draft: string;
  /** Tools the assistant ran this turn, in order. */
  toolCalls: ToolCallEvent[];
  isStreaming: boolean;
  error: string | null;
}

const IDLE: StreamState = {
  draft: "",
  toolCalls: [],
  isStreaming: false,
  error: null,
};

/**
 * Stream a chat turn over SSE, accumulating tokens and tool calls into local
 * state. On completion it invalidates the conversation queries so the
 * persisted history replaces the live draft.
 */
export function useStreamChat() {
  const queryClient = useQueryClient();
  const [state, setState] = useState<StreamState>(IDLE);

  const reset = useCallback(() => setState(IDLE), []);

  const send = useCallback(
    async (body: ChatRequestBody, onConversation?: (id: number) => void) => {
      setState({ ...IDLE, isStreaming: true });
      let conversationId: number | null = null;
      try {
        await streamChat(body, (event) => {
          switch (event.type) {
            case "conversation":
              conversationId = event.conversation_id;
              onConversation?.(event.conversation_id);
              break;
            case "tool_call":
              setState((prev) => ({
                ...prev,
                toolCalls: [...prev.toolCalls, event],
              }));
              break;
            case "token":
              setState((prev) => ({ ...prev, draft: prev.draft + event.text }));
              break;
            case "done":
              conversationId = event.conversation_id;
              break;
            case "error":
              setState((prev) => ({ ...prev, error: event.detail }));
              break;
          }
        });
      } catch (err) {
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : "stream failed",
        }));
      } finally {
        // Refresh the list and the affected thread so persisted turns replace
        // the live draft (covers both the done and error paths).
        queryClient.invalidateQueries({ queryKey: KEYS.conversations });
        if (conversationId !== null) {
          queryClient.invalidateQueries({
            queryKey: KEYS.conversation(conversationId),
          });
        }
        setState((prev) => ({ ...prev, isStreaming: false }));
      }
    },
    [queryClient],
  );

  return { ...state, send, reset };
}
