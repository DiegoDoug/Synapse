/**
 * React Query hooks for the AI assistant. Encapsulates query keys and cache
 * invalidation so components stay declarative.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type AIHealthDto,
  type ChatRequestBody,
  type ChatResultDto,
  type ConversationDetailDto,
  type ConversationDto,
  type SystemPromptDto,
  fetchAIHealth,
  fetchConversation,
  fetchConversations,
  fetchPrompts,
  sendChat,
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
