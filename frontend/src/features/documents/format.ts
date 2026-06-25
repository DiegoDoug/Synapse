/** Presentation helpers for documents — byte sizes, dates, and status chips. */

import type { DocumentStatus } from "@/features/documents/api";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
}

interface StatusMeta {
  label: string;
  /** Tailwind classes for the badge. */
  className: string;
}

export function statusMeta(status: DocumentStatus | string): StatusMeta {
  switch (status) {
    case "indexed":
      return {
        label: "Indexed",
        className:
          "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
      };
    case "indexing":
      return {
        label: "Indexing…",
        className: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
      };
    case "unavailable":
      return {
        label: "Embeddings off",
        className: "bg-muted text-muted-foreground",
      };
    case "failed":
      return {
        label: "Failed",
        className: "bg-destructive/15 text-destructive",
      };
    default:
      return {
        label: "Pending",
        className: "bg-muted text-muted-foreground",
      };
  }
}
