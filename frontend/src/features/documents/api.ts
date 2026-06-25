/**
 * Documents (knowledge base) API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/document.py. No React/state here.
 */

import { apiDelete, apiGet, apiUpload } from "@/api/client";

export interface KnowledgeHit {
  document_id: number;
  filename: string;
  chunk_index: number;
  content: string;
  score: number;
}

export interface KnowledgeSearchResponse {
  query: string;
  available: boolean;
  hits: KnowledgeHit[];
}

export type DocumentStatus =
  | "pending"
  | "indexing"
  | "indexed"
  | "unavailable"
  | "failed";

export interface DocumentDto {
  id: number;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  status: DocumentStatus | string;
  error: string | null;
  char_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  indexed_at: string | null;
}

export interface KnowledgeStatusDto {
  embeddings_available: boolean;
  embedding_model: string;
  vector_backend: string;
}

export function fetchDocuments(): Promise<DocumentDto[]> {
  return apiGet<DocumentDto[]>("/documents");
}

export function fetchKnowledgeStatus(): Promise<KnowledgeStatusDto> {
  return apiGet<KnowledgeStatusDto>("/documents/status");
}

export function uploadDocument(file: File): Promise<DocumentDto> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<DocumentDto>("/documents/upload", form);
}

export function deleteDocument(id: number): Promise<void> {
  return apiDelete(`/documents/${id}`);
}

export function searchKnowledge(
  query: string,
  limit = 5,
): Promise<KnowledgeSearchResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return apiGet<KnowledgeSearchResponse>(`/knowledge/search?${params.toString()}`);
}
