import { Cpu } from "lucide-react";

import { useAIHealth } from "@/features/ai/useAssistant";
import { cn } from "@/lib/utils";

/** Small badge showing the active LLM provider, model, and availability. */
export default function ProviderIndicator() {
  const { data, isLoading } = useAIHealth();

  if (isLoading || !data) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
        <Cpu className="h-3.5 w-3.5" />
        Checking provider…
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground"
      title={data.available ? "Provider configured" : "Provider not configured"}
    >
      <span
        className={cn(
          "inline-block h-2 w-2 rounded-full",
          data.available ? "bg-emerald-500" : "bg-amber-500",
        )}
      />
      <span className="font-medium capitalize text-foreground">
        {data.provider}
      </span>
      <span className="text-muted-foreground">{data.model}</span>
    </span>
  );
}
