import { Loader2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface DocumentUploadProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
  /** Optional error message from the last upload attempt. */
  error?: string | null;
}

const ACCEPT = ".txt,.md,.markdown,.csv,.rst,.log,.pdf,text/plain,application/pdf";

/** Drag-and-drop (and click-to-browse) file uploader for the knowledge base. */
export function DocumentUpload({ onUpload, isUploading, error }: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onUpload(file);
  };

  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        disabled={isUploading}
        aria-label="Upload a document"
        className={cn(
          "flex w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-card px-4 py-8 text-center transition-colors",
          "hover:border-primary/50 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60",
          dragging && "border-primary bg-accent/60",
        )}
      >
        {isUploading ? (
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        ) : (
          <Upload className="h-6 w-6 text-muted-foreground" />
        )}
        <span className="text-sm font-medium">
          {isUploading ? "Uploading…" : "Drop a file here or click to browse"}
        </span>
        <span className="text-xs text-muted-foreground">
          Text, Markdown, or PDF · up to 10 MB
        </span>
      </button>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </div>
  );
}
