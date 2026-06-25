import { FileText } from "lucide-react";

import type { DocumentDto } from "@/features/documents/api";
import { DocumentCard } from "@/features/documents/components/DocumentCard";

interface DocumentListProps {
  documents: DocumentDto[];
  isLoading?: boolean;
  isError?: boolean;
  onDelete: (id: number) => void;
  deletingId?: number;
}

/** Renders the document list with loading / error / empty states. */
export function DocumentList({
  documents,
  isLoading = false,
  isError = false,
  onDelete,
  deletingId,
}: DocumentListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="h-20 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">
        Couldn&apos;t load your documents. Try again.
      </p>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
        <FileText className="h-6 w-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          No documents yet. Upload one to ground the assistant in your knowledge.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((document) => (
        <DocumentCard
          key={document.id}
          document={document}
          onDelete={onDelete}
          deleting={deletingId === document.id}
        />
      ))}
    </div>
  );
}
