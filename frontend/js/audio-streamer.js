/**
 * AudioStreamer — captures microphone audio at 16kHz PCM via AudioWorklet
 * and streams it to the backend WebSocket as base64-encoded JSON messages.
 *
 * Features:
 *   - AudioWorklet-based capture (low latency, off main thread)
 *   - Automatic 16kHz resampling via AudioContext
 *   - AnalyserNode for input waveform visualization
 *   - Start / stop / mute controls
 */
export class AudioStreamer {
    constructor() {
        this._ctx = null;
        this._stream = null;
        this._source = null;
        this._workletNode = null;
        this._analyser = null;
        this._ws = null;
        this._isStreaming = false;
    }

    /**
     * Start capturing microphone audio and streaming to the WebSocket.
     * @param {WebSocket} ws - An open WebSocket connection
     */
    async start(ws) {
        this._ws = ws;

        // Request microphone access
        this._stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });

        // Create AudioContext at 16kHz (browser will resample automatically)
        this._ctx = new AudioContext({ sampleRate: 16000 });

        // Register the PCM processor worklet
        await this._ctx.audioWorklet.addModule("/static/worklet/pcm-processor.js");

        // Create nodes
        this._source = this._ctx.createMediaStreamSource(this._stream);
        this._workletNode = new AudioWorkletNode(this._ctx, "pcm16-processor");

        // Analyser for input visualization
        this._analyser = this._ctx.createAnalyser();
        this._analyser.fftSize = 256;
        this._analyser.smoothingTimeConstant = 0.7;

        // Connect: mic → analyser → worklet
        this._source.connect(this._analyser);
        this._analyser.connect(this._workletNode);
        this._workletNode.connect(this._ctx.destination);

        // Listen for PCM chunks from the worklet
        this._workletNode.port.onmessage = (event) => {
            if (!this._isStreaming || !this._ws) return;
            if (this._ws.readyState !== WebSocket.OPEN) return;

            // Convert ArrayBuffer → base64
            const buffer = event.data;
            const bytes = new Uint8Array(buffer);
            const base64 = this._arrayBufferToBase64(bytes);

            this._ws.send(
                JSON.stringify({ type: "audio", data: base64 })
            );
        };

        this._isStreaming = true;
    }

    /** Stop streaming and release the microphone. */
    async stop() {
        this._isStreaming = false;

        // Stop the worklet
        if (this._workletNode) {
            this._workletNode.port.postMessage("stop");
            this._workletNode.disconnect();
            this._workletNode = null;
        }

        // Disconnect source
        if (this._source) {
            this._source.disconnect();
            this._source = null;
        }

        // Stop media tracks
        if (this._stream) {
            this._stream.getTracks().forEach((t) => t.stop());
            this._stream = null;
        }

        // Close audio context
        if (this._ctx) {
            await this._ctx.close();
            this._ctx = null;
        }

        this._analyser = null;
    }

    /** Get frequency data for input visualization. */
    getFrequencyData() {
        if (!this._analyser) return new Uint8Array(0);
        const data = new Uint8Array(this._analyser.frequencyBinCount);
        this._analyser.getByteFrequencyData(data);
        return data;
    }

    get isStreaming() {
        return this._isStreaming;
    }

    /**
     * Convert a Uint8Array to a base64 string.
     * @param {Uint8Array} bytes
     * @returns {string}
     */
    _arrayBufferToBase64(bytes) {
        let binary = "";
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
}
