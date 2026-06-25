/**
 * AI assistant API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/ai.py. No React/state here.
 */

import { apiGet, apiPost } from "@/api/client";
import { type PendingActionDto } from "@/features/actions/api";

const API_BASE = "/api/v1";

export type MessageRole = "user" | "assistant" | "system" | "tool";

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
  pending_actions: PendingActionDto[];
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

// --- SSE streaming ---------------------------------------------------------

export interface ToolCallEvent {
  name: string;
  arguments: Record<string, unknown>;
  summary: string;
}

export type StreamEvent =
  | { type: "conversation"; conversation_id: number }
  | ({ type: "tool_call" } & ToolCallEvent)
  | ({ type: "pending_action" } & PendingActionDto)
  | { type: "token"; text: string }
  | {
      type: "done";
      message_id: number;
      conversation_id: number;
      provider: string;
      model: string;
    }
  | { type: "error"; detail: string };

/**
 * POST a chat message and consume the Server-Sent Events stream, invoking
 * `onEvent` for each parsed event. Resolves when the stream closes.
 */
export async function streamChat(
  body: ChatRequestBody,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/ai/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) {
    throw new Error(`stream failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const dataLine = frame
        .split("\n")
        .find((line) => line.startsWith("data:"));
      if (!dataLine) continue;
      const payload = dataLine.slice(5).trim();
      if (payload) onEvent(JSON.parse(payload) as StreamEvent);
    }
  }
}
