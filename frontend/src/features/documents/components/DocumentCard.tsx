import { FileText, Loader2, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { DocumentDto } from "@/features/documents/api";
import { formatBytes, formatDate, statusMeta } from "@/features/documents/format";
import { cn } from "@/lib/utils";

interface DocumentCardProps {
  document: DocumentDto;
  onDelete: (id: number) => void;
  deleting?: boolean;
}

/** A single knowledge-base document: name, status, size, and a delete action. */
export function DocumentCard({ document, onDelete, deleting }: DocumentCardProps) {
  const status = statusMeta(document.status);

  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-4">
      <FileText className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-medium" title={document.filename}>
            {document.filename}
          </p>
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
              status.className,
            )}
          >
            {status.label}
          </span>
        </div>

        <p className="mt-1 text-xs text-muted-foreground">
          {formatBytes(document.size_bytes)}
          {document.chunk_count > 0 && ` · ${document.chunk_count} chunks`}
          {` · added ${formatDate(document.created_at)}`}
        </p>

        {document.status === "failed" && document.error && (
          <p className="mt-1 text-xs text-destructive">{document.error}</p>
        )}
        {document.status === "unavailable" && (
          <p className="mt-1 text-xs text-muted-foreground">
            Stored, but not searchable yet — embeddings aren&apos;t installed.
          </p>
        )}
      </div>

      <Button
        variant="ghost"
        size="icon"
        aria-label={`Delete ${document.filename}`}
        disabled={deleting}
        onClick={() => onDelete(document.id)}
      >
        {deleting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Trash2 className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}
