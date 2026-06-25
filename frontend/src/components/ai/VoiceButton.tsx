import { Loader2, Mic, Square } from "lucide-react";
import { useCallback } from "react";

import { Button } from "@/components/ui/button";
import { useVoice } from "@/features/voice/useVoice";
import { cn } from "@/lib/utils";

interface VoiceButtonProps {
  /** Called with the transcript once a recording is captured + transcribed. */
  onTranscript: (text: string) => void;
  /** Disable interaction (e.g. STT unavailable or a turn is streaming). */
  disabled?: boolean;
}

/**
 * Push-to-talk button: press and hold to record, release to transcribe. The
 * transcript is handed to `onTranscript` (the Assistant page injects it into
 * the normal chat flow). Shows a recording pulse and a transcribing spinner.
 */
export default function VoiceButton({ onTranscript, disabled }: VoiceButtonProps) {
  const { status, error, start, stop } = useVoice();
  const recording = status === "recording";
  const busy = status === "transcribing";

  const begin = useCallback(() => {
    if (disabled || busy) return;
    void start();
  }, [disabled, busy, start]);

  const end = useCallback(async () => {
    if (!recording) return;
    const text = await stop();
    if (text) onTranscript(text);
  }, [recording, stop, onTranscript]);

  return (
    <Button
      type="button"
      size="icon"
      variant={recording ? "default" : "outline"}
      disabled={disabled || busy}
      // Pointer events cover mouse + touch; release/leave ends the recording.
      onPointerDown={begin}
      onPointerUp={() => void end()}
      onPointerLeave={() => void end()}
      title={
        error ??
        (recording ? "Release to send" : "Hold to talk")
      }
      aria-label={recording ? "Recording — release to send" : "Hold to talk"}
      className={cn(recording && "animate-pulse ring-2 ring-ring")}
    >
      {busy ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : recording ? (
        <Square className="h-4 w-4" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
    </Button>
  );
}
