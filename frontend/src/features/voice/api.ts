/**
 * Voice API layer — DTO types and typed fetchers.
 * Mirrors backend/schemas/voice.py. No React/state here.
 */

import { apiGet } from "@/api/client";

const API_BASE = "/api/v1";

export interface VoiceConfigDto {
  stt_available: boolean;
  tts_available: boolean;
  whisper_model: string;
  tts_voice: string;
}

export interface TranscriptDto {
  text: string;
}

export function fetchVoiceConfig(): Promise<VoiceConfigDto> {
  return apiGet<VoiceConfigDto>("/voice/config");
}

/** Upload a recorded audio clip and return its transcript text. */
export async function transcribeAudio(audio: Blob): Promise<TranscriptDto> {
  const form = new FormData();
  form.append("file", audio, "clip.webm");
  const response = await fetch(`${API_BASE}/voice/transcribe`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(`transcribe failed: ${response.status}`);
  }
  return response.json() as Promise<TranscriptDto>;
}

/** Synthesize speech for `text` and return the audio as a Blob (WAV). */
export async function synthesizeSpeech(
  text: string,
  voice?: string,
): Promise<Blob> {
  const response = await fetch(`${API_BASE}/voice/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice: voice ?? null }),
  });
  if (!response.ok) {
    throw new Error(`synthesize failed: ${response.status}`);
  }
  return response.blob();
}
