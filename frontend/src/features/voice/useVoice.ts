/**
 * Voice hooks — capabilities query, push-to-talk recording, and TTS playback.
 *
 * `useVoiceConfig` reports whether the backend's local STT/TTS models are
 * available so the UI can disable controls. `useVoice` owns a small recording
 * state machine over MediaRecorder: `start()` opens the mic, `stop()` resolves
 * the transcript, and `speak()` plays synthesized speech for a reply.
 */

import { useQuery } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import {
  fetchVoiceConfig,
  synthesizeSpeech,
  transcribeAudio,
  type VoiceConfigDto,
} from "@/features/voice/api";

export function useVoiceConfig() {
  return useQuery<VoiceConfigDto>({
    queryKey: ["voice", "config"],
    queryFn: fetchVoiceConfig,
    staleTime: 5 * 60 * 1000,
  });
}

export type VoiceStatus = "idle" | "recording" | "transcribing" | "error";

export function useVoice() {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  /** Open the mic and begin recording. No-op if already recording. */
  const start = useCallback(async () => {
    if (status === "recording") return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.start();
      recorderRef.current = recorder;
      setStatus("recording");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Microphone unavailable");
    }
  }, [status]);

  /**
   * Stop recording, transcribe the clip, and return the text. Returns an empty
   * string on error (with `status` set to "error").
   */
  const stop = useCallback(async (): Promise<string> => {
    const recorder = recorderRef.current;
    if (!recorder || status !== "recording") return "";

    const blob = await new Promise<Blob>((resolve) => {
      recorder.onstop = () =>
        resolve(new Blob(chunksRef.current, { type: "audio/webm" }));
      recorder.stop();
    });
    stopTracks();
    recorderRef.current = null;

    setStatus("transcribing");
    try {
      const { text } = await transcribeAudio(blob);
      setStatus("idle");
      return text.trim();
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Transcription failed");
      return "";
    }
  }, [status, stopTracks]);

  /** Synthesize `text` and play it back. Errors are swallowed (best-effort). */
  const speak = useCallback(async (text: string) => {
    if (!text.trim()) return;
    try {
      const blob = await synthesizeSpeech(text);
      const url = URL.createObjectURL(blob);
      audioRef.current?.pause();
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      // Best-effort playback; a TTS failure should never break the chat.
    }
  }, []);

  return { status, error, start, stop, speak };
}
