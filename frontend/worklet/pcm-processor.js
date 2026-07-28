/**
 * PCM16 AudioWorklet Processor
 *
 * Captures raw Float32 audio samples from the microphone,
 * converts them to 16-bit signed PCM (Int16), and posts
 * the binary buffer to the main thread for WebSocket streaming.
 *
 * Runs in a separate audio rendering thread for minimal latency.
 */
class PCM16Processor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._active = true;

        this.port.onmessage = (event) => {
            if (event.data === "stop") {
                this._active = false;
            }
        };
    }

    /**
     * Process 128-sample audio frames.
     * @param {Float32Array[][]} inputs  - Input audio channels
     * @returns {boolean} - true to keep processor alive
     */
    process(inputs) {
        if (!this._active) return false;

        const input = inputs[0];
        if (!input || !input[0]) return true;

        const samples = input[0]; // Mono channel

        // Convert Float32 (-1.0 … 1.0) → Int16 (-32768 … 32767)
        const pcm16 = new Int16Array(samples.length);
        for (let i = 0; i < samples.length; i++) {
            const s = Math.max(-1, Math.min(1, samples[i]));
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Transfer the underlying ArrayBuffer to the main thread
        this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
        return true;
    }
}

registerProcessor("pcm16-processor", PCM16Processor);
