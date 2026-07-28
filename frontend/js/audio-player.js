/**
 * AudioPlayer — plays incoming 24kHz PCM audio chunks from the Gemini
 * Live API using the Web Audio API with gapless buffer scheduling.
 *
 * Features:
 *   - Gapless playback of streamed PCM chunks
 *   - Instant interrupt (barge-in) support
 *   - AnalyserNode for waveform / frequency visualization
 */
export class AudioPlayer {
    constructor() {
        this._ctx = null;
        this._analyser = null;
        this._gainNode = null;
        this._queue = [];
        this._nextStartTime = 0;
        this._isPlaying = false;
        this._sources = [];

        // Output sample rate from Gemini Live API
        this.SAMPLE_RATE = 24000;
    }

    /** Initialize the AudioContext (must be called after user gesture). */
    async init() {
        if (this._ctx) return;

        this._ctx = new AudioContext({ sampleRate: this.SAMPLE_RATE });

        // Analyser for visualization
        this._analyser = this._ctx.createAnalyser();
        this._analyser.fftSize = 256;
        this._analyser.smoothingTimeConstant = 0.8;

        // Gain node for volume control
        this._gainNode = this._ctx.createGain();
        this._gainNode.gain.value = 1.0;
        this._gainNode.connect(this._analyser);
        this._analyser.connect(this._ctx.destination);
    }

    /**
     * Enqueue and schedule a base64-encoded PCM audio chunk for playback.
     * @param {string} base64Data - Base64-encoded raw 16-bit PCM at 24kHz
     */
    playChunk(base64Data) {
        if (!this._ctx) return;

        // Decode base64 → ArrayBuffer
        const binaryStr = atob(base64Data);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
        }

        // Convert Int16 PCM → Float32 samples
        const int16 = new Int16Array(bytes.buffer);
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
            float32[i] = int16[i] / 32768;
        }

        // Create AudioBuffer
        const audioBuffer = this._ctx.createBuffer(1, float32.length, this.SAMPLE_RATE);
        audioBuffer.getChannelData(0).set(float32);

        // Schedule gapless playback
        const source = this._ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this._gainNode);

        const now = this._ctx.currentTime;
        const startTime = Math.max(now, this._nextStartTime);
        source.start(startTime);

        this._nextStartTime = startTime + audioBuffer.duration;
        this._isPlaying = true;

        // Track active sources for interrupt
        this._sources.push(source);
        source.onended = () => {
            const idx = this._sources.indexOf(source);
            if (idx > -1) this._sources.splice(idx, 1);
            if (this._sources.length === 0) {
                this._isPlaying = false;
            }
        };
    }

    /**
     * Immediately stop all playback and clear the queue.
     * Used for barge-in interruption.
     */
    interrupt() {
        for (const source of this._sources) {
            try {
                source.stop();
            } catch (e) {
                // Already stopped
            }
        }
        this._sources = [];
        this._nextStartTime = 0;
        this._isPlaying = false;
    }

    /** Get frequency data for visualization (Uint8Array). */
    getFrequencyData() {
        if (!this._analyser) return new Uint8Array(0);
        const data = new Uint8Array(this._analyser.frequencyBinCount);
        this._analyser.getByteFrequencyData(data);
        return data;
    }

    /** Get time-domain waveform data for visualization (Uint8Array). */
    getTimeDomainData() {
        if (!this._analyser) return new Uint8Array(0);
        const data = new Uint8Array(this._analyser.frequencyBinCount);
        this._analyser.getByteTimeDomainData(data);
        return data;
    }

    get isPlaying() {
        return this._isPlaying;
    }

    async close() {
        this.interrupt();
        if (this._ctx) {
            await this._ctx.close();
            this._ctx = null;
        }
    }
}
