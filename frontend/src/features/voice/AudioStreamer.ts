/**
 * AudioStreamer — capture the mic, resample to 16 kHz PCM in an AudioWorklet,
 * and stream the frames over the wake-word WebSocket. Server events (ready /
 * wake_word_detected / listening / transcript / unavailable / error) are handed
 * to `onEvent`. One instance per active wake-word session; call `stop()` to
 * release the mic and socket.
 */

export interface WakeEvent {
  event:
    | "ready"
    | "wake_word_detected"
    | "listening"
    | "transcript"
    | "unavailable"
    | "error";
  text?: string;
  detail?: string;
}

function wsUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/voice/ws`;
}

export class AudioStreamer {
  private socket: WebSocket | null = null;
  private context: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;
  private stopped = false;

  constructor(private readonly onEvent: (event: WakeEvent) => void) {}

  async start(): Promise<void> {
    this.stopped = false;
    this.socket = new WebSocket(wsUrl());
    this.socket.binaryType = "arraybuffer";
    this.socket.onmessage = (message) => {
      try {
        this.onEvent(JSON.parse(message.data as string) as WakeEvent);
      } catch {
        // Ignore malformed frames.
      }
    };
    this.socket.onerror = () =>
      this.onEvent({ event: "error", detail: "WebSocket error" });

    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.context = new AudioContext();
    await this.context.audioWorklet.addModule("/pcm-worklet.js");
    if (this.stopped) return this.stop();

    const source = this.context.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.context, "pcm-worklet");
    this.node.port.onmessage = (event) => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(event.data as ArrayBuffer);
      }
    };
    source.connect(this.node);
    // Keep the graph pulling without audible output.
    this.node.connect(this.context.destination);
  }

  stop(): void {
    this.stopped = true;
    this.node?.disconnect();
    this.node = null;
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    void this.context?.close();
    this.context = null;
    if (this.socket && this.socket.readyState <= WebSocket.OPEN) {
      this.socket.close();
    }
    this.socket = null;
  }
}
