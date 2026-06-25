// AudioWorklet processor for wake-word streaming (Stage 4.7).
//
// Receives mic audio at the AudioContext sample rate, resamples to 16 kHz, and
// posts ~80 ms frames of mono int16 PCM to the main thread (which forwards them
// over the /voice/ws WebSocket). Kept dependency-free — worklets run in a
// separate realm and can't import application code.

const TARGET_RATE = 16000;
const FRAME_SAMPLES = 1280; // 80 ms at 16 kHz

class PcmWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this._ratio = sampleRate / TARGET_RATE; // sampleRate is a worklet global
    this._pos = 0; // fractional read position into the input stream
    this._acc = []; // resampled int16 samples awaiting a full frame
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;

    // Linear-interpolate down to 16 kHz.
    for (; this._pos < channel.length; this._pos += this._ratio) {
      const i = Math.floor(this._pos);
      const frac = this._pos - i;
      const a = channel[i] ?? 0;
      const b = channel[i + 1] ?? a;
      const sample = a + (b - a) * frac;
      const clamped = Math.max(-1, Math.min(1, sample));
      this._acc.push(clamped * 0x7fff);

      if (this._acc.length >= FRAME_SAMPLES) {
        const frame = new Int16Array(this._acc.splice(0, FRAME_SAMPLES));
        this.port.postMessage(frame.buffer, [frame.buffer]);
      }
    }
    // Carry the fractional remainder into the next block.
    this._pos -= channel.length;
    return true;
  }
}

registerProcessor("pcm-worklet", PcmWorklet);
