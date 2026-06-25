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

/** A labeled on/off switch. */
function Toggle({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-sm">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-40",
          checked ? "bg-primary" : "bg-muted-foreground/30",
        )}
      >
        <span
          className={cn(
            "inline-block h-4 w-4 rounded-full bg-background transition-transform",
            checked ? "translate-x-4" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  );
}

/**
 * Voice settings — local STT / TTS / wake-word status and their toggles.
 *
 * Model size and voice are configured in the backend environment for now and
 * shown read-only. The wake-word toggle arms continuous listening on the
 * Assistant page; it's disabled until the wake-word model is installed.
 */
export default function VoiceSettings() {
  const config = useVoiceConfig();
  const autoRead = useAppStore((state) => state.voiceAutoRead);
  const setAutoRead = useAppStore((state) => state.setVoiceAutoRead);
  const wakeWord = useAppStore((state) => state.voiceWakeWord);
  const setWakeWord = useAppStore((state) => state.setVoiceWakeWord);

  const stt = config.data?.stt_available ?? false;
  const tts = config.data?.tts_available ?? false;
  const wake = config.data?.wake_word_available ?? false;

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
        <Capability
          label="Wake word"
          value={config.data?.wake_word_model ?? "—"}
          ok={wake}
        />

        <Toggle
          label="Read replies aloud"
          checked={autoRead}
          disabled={!tts}
          onChange={setAutoRead}
        />
        <Toggle
          label="Wake-word listening"
          checked={wakeWord}
          disabled={!wake}
          onChange={setWakeWord}
        />

        {(!stt || !tts || !wake) && (
          <p className="text-sm text-muted-foreground">
            Install the backend voice extras to enable these:{" "}
            <code>pip install -r backend/requirements-voice.txt</code>, then
            restart the server. The wake word uses a pretrained model; a custom
            phrase is future work.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
