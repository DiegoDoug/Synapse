import { DocumentList } from "@/features/documents/components/DocumentList";
import { DocumentUpload } from "@/features/documents/components/DocumentUpload";
import {
  useDeleteDocument,
  useDocuments,
  useKnowledgeStatus,
  useUploadDocument,
} from "@/features/documents/useDocuments";

/** Knowledge base — upload, list, and delete documents that ground the AI. */
export default function DocumentsPage() {
  const documents = useDocuments();
  const status = useKnowledgeStatus();
  const upload = useUploadDocument();
  const remove = useDeleteDocument();

  const embeddingsOff = status.data && !status.data.embeddings_available;

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Knowledge Base</h1>
        <p className="text-sm text-muted-foreground">
          Upload documents so the assistant can ground its answers in your own
          notes, plans, and references.
        </p>
      </div>

      {embeddingsOff && (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          Semantic search is offline — the embedding model isn&apos;t installed.
          Documents are stored and can be re-indexed later. Install{" "}
          <code>backend/requirements-knowledge.txt</code> to enable grounded
          answers.
        </p>
      )}

      <DocumentUpload
        onUpload={(file) => upload.mutate(file)}
        isUploading={upload.isPending}
        error={upload.isError ? "Upload failed. Try a different file." : null}
      />

      <DocumentList
        documents={documents.data ?? []}
        isLoading={documents.isLoading}
        isError={documents.isError}
        onDelete={(id) => remove.mutate(id)}
        deletingId={remove.isPending ? (remove.variables as number) : undefined}
      />
    </div>
  );
}
