import { FileText, Loader2, Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { KnowledgeHit } from "@/features/documents/api";
import { useKnowledgeSearch } from "@/features/documents/useDocuments";

/** Semantic search box + ranked results over the knowledge base. */
export function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const search = useKnowledgeSearch();
  const response = search.data;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) search.mutate(trimmed);
  };

  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your documents…"
            aria-label="Search your documents"
            className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <Button type="submit" size="sm" disabled={search.isPending || !query.trim()}>
          {search.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Search"
          )}
        </Button>
      </form>

      {search.isError && (
        <p className="text-sm text-destructive">Search failed. Try again.</p>
      )}

      {response && !response.available && (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          Semantic search is offline — the embedding model isn&apos;t installed.
        </p>
      )}

      {response && response.available && response.hits.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No matching passages for “{response.query}”.
        </p>
      )}

      {response && response.hits.length > 0 && (
        <ul className="space-y-2">
          {response.hits.map((hit, index) => (
            <KnowledgeResult key={`${hit.document_id}-${hit.chunk_index}`} hit={hit} rank={index + 1} />
          ))}
        </ul>
      )}
    </div>
  );
}

interface KnowledgeResultProps {
  hit: KnowledgeHit;
  rank: number;
}

/** A single search result: source filename, relevance, and the matched excerpt. */
function KnowledgeResult({ hit, rank }: KnowledgeResultProps) {
  return (
    <li className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-muted text-[11px] font-medium text-foreground">
          {rank}
        </span>
        <FileText className="h-3.5 w-3.5" />
        <span className="font-medium text-foreground">{hit.filename}</span>
        <span className="ml-auto tabular-nums">
          {(hit.score * 100).toFixed(0)}% match
        </span>
      </div>
      <p className="mt-2 line-clamp-4 text-sm text-card-foreground">{hit.content}</p>
    </li>
  );
}
