/**
 * React Query hooks for the knowledge base. Encapsulates query keys and cache
 * invalidation so components stay declarative.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type DocumentDto,
  type KnowledgeStatusDto,
  deleteDocument,
  fetchDocuments,
  fetchKnowledgeStatus,
  uploadDocument,
} from "@/features/documents/api";

const KEYS = {
  all: ["documents"] as const,
  list: ["documents", "list"] as const,
  status: ["documents", "status"] as const,
};

export function useDocuments() {
  return useQuery<DocumentDto[]>({
    queryKey: KEYS.list,
    queryFn: fetchDocuments,
    // A freshly uploaded file may still be indexing; poll briefly so the badge
    // settles without the user refreshing.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((d) => d.status === "indexing")
        ? 2000
        : false,
  });
}

export function useKnowledgeStatus() {
  return useQuery<KnowledgeStatusDto>({
    queryKey: KEYS.status,
    queryFn: fetchKnowledgeStatus,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEYS.list }),
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteDocument(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEYS.list }),
  });
}
