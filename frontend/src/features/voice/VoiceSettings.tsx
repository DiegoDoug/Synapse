import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useVoiceConfig } from "@/features/voice/useVoice";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";

/** Status dot + label for a capability row. */
function Capability({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-sm">{label}</span>
      <span className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">{value}</span>
        <span
          className={cn(
            "inline-block h-2.5 w-2.5 rounded-full",
            ok ? "bg-emerald-500" : "bg-muted-foreground/40",
          )}
        />
      </span>
    </div>
  );
}

/**
 * Voice settings — local STT/TTS status and the read-back toggle.
 *
 * Model size and voice are configured in the backend environment for now and
 * shown here read-only. The wake-word toggle is reserved for wake-word mode
 * (Stage 4.7 Major Feature 2) and is disabled until then.
 */
export default function VoiceSettings() {
  const config = useVoiceConfig();
  const autoRead = useAppStore((state) => state.voiceAutoRead);
  const setAutoRead = useAppStore((state) => state.setVoiceAutoRead);

  const stt = config.data?.stt_available ?? false;
  const tts = config.data?.tts_available ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Voice</CardTitle>
        <CardDescription>
          Talk to the assistant with local speech-to-text and have replies read
          back. All processing stays on the device.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Capability
          label="Speech-to-text"
          value={config.data?.whisper_model ?? "—"}
          ok={stt}
        />
        <Capability
          label="Text-to-speech"
          value={config.data?.tts_voice ?? "—"}
          ok={tts}
        />

        <div className="flex items-center justify-between gap-2">
          <span className="text-sm">Read replies aloud</span>
          <button
            type="button"
            role="switch"
            aria-checked={autoRead}
            disabled={!tts}
            onClick={() => setAutoRead(!autoRead)}
            className={cn(
              "relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-40",
              autoRead ? "bg-primary" : "bg-muted-foreground/30",
            )}
          >
            <span
              className={cn(
                "inline-block h-4 w-4 rounded-full bg-background transition-transform",
                autoRead ? "translate-x-4" : "translate-x-0.5",
              )}
            />
          </button>
        </div>

        {(!stt || !tts) && (
          <p className="text-sm text-muted-foreground">
            Install the backend voice extras to enable this:{" "}
            <code>pip install -r backend/requirements-voice.txt</code>, then
            restart the server.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
