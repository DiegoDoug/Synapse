/**
 * AI assistant API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/ai.py. No React/state here.
 */

import { apiGet, apiPost } from "@/api/client";

export type MessageRole = "user" | "assistant" | "system";

export interface MessageDto {
  id: number;
  conversation_id: number;
  role: MessageRole | string;
  content: string;
  provider: string | null;
  model: string | null;
  created_at: string;
}

export interface ConversationDto {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetailDto extends ConversationDto {
  messages: MessageDto[];
}

export interface SystemPromptDto {
  id: number;
  name: string;
  description: string | null;
  system_prompt: string;
}

export interface AIHealthDto {
  provider: string;
  model: string;
  available: boolean;
}

export interface ChatResultDto {
  conversation_id: number;
  message: MessageDto;
  provider: string;
  model: string;
  metadata: Record<string, unknown>;
}

export interface ChatRequestBody {
  message: string;
  conversation_id?: number;
  system_prompt_id?: number;
}

export function sendChat(body: ChatRequestBody): Promise<ChatResultDto> {
  return apiPost<ChatResultDto>("/ai/chat", body);
}

export function fetchAIHealth(): Promise<AIHealthDto> {
  return apiGet<AIHealthDto>("/ai/health");
}

export function fetchConversations(): Promise<ConversationDto[]> {
  return apiGet<ConversationDto[]>("/conversations");
}

export function fetchConversation(id: number): Promise<ConversationDetailDto> {
  return apiGet<ConversationDetailDto>(`/conversations/${id}`);
}

export function createConversation(title?: string): Promise<ConversationDto> {
  return apiPost<ConversationDto>("/conversations", { title: title ?? null });
}

export function fetchPrompts(): Promise<SystemPromptDto[]> {
  return apiGet<SystemPromptDto[]>("/prompts");
}
