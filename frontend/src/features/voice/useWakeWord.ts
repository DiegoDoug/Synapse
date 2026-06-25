/**
 * useWakeWord — drive the opt-in "wake word" mode.
 *
 * Opens an `AudioStreamer` that streams mic PCM to `/voice/ws`; when the backend
 * detects the wake word it records the following utterance, transcribes it, and
 * sends back the text — which this hook forwards to `onTranscript` (the
 * Assistant page injects it into the normal chat flow, so wake-word input reuses
 * the same tool-use + confirmation path as everything else).
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { AudioStreamer, type WakeEvent } from "@/features/voice/AudioStreamer";

export type WakeWordStatus =
  | "off"
  | "connecting"
  | "armed" // listening for the wake word
  | "recording" // wake word heard, capturing the utterance
  | "error";

export function useWakeWord(onTranscript: (text: string) => void) {
  const [status, setStatus] = useState<WakeWordStatus>("off");
  const [error, setError] = useState<string | null>(null);
  const streamerRef = useRef<AudioStreamer | null>(null);
  // Keep the latest callback without restarting the stream.
  const transcriptRef = useRef(onTranscript);
  transcriptRef.current = onTranscript;

  const handleEvent = useCallback((event: WakeEvent) => {
    switch (event.event) {
      case "ready":
      case "listening":
        setStatus("armed");
        break;
      case "wake_word_detected":
        setStatus("recording");
        break;
      case "transcript":
        setStatus("armed");
        if (event.text) transcriptRef.current(event.text);
        break;
      case "unavailable":
        setError(event.detail ?? "Wake word unavailable");
        setStatus("error");
        break;
      case "error":
        setError(event.detail ?? "Wake-word error");
        break;
    }
  }, []);

  const stop = useCallback(() => {
    streamerRef.current?.stop();
    streamerRef.current = null;
    setStatus("off");
  }, []);

  const start = useCallback(async () => {
    if (streamerRef.current) return;
    setError(null);
    setStatus("connecting");
    const streamer = new AudioStreamer(handleEvent);
    streamerRef.current = streamer;
    try {
      await streamer.start();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone unavailable");
      setStatus("error");
      streamer.stop();
      streamerRef.current = null;
    }
  }, [handleEvent]);

  // Release the mic/socket if the component unmounts mid-session.
  useEffect(() => () => streamerRef.current?.stop(), []);

  return { status, error, start, stop };
}
