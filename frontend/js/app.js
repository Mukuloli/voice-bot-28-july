/**
 * Voice Bot — Main Application Controller
 *
 * Manages the UI state machine, WebSocket lifecycle,
 * waveform visualization, and user interactions.
 */
import { AudioStreamer } from "./audio-streamer.js";
import { AudioPlayer } from "./audio-player.js";

// ── State Machine ───────────────────────────────────────────────────
const State = {
    IDLE: "idle",
    CONNECTING: "connecting",
    LISTENING: "listening",
    SPEAKING: "speaking",
    ERROR: "error",
};

// ── DOM References ──────────────────────────────────────────────────
const micBtn = document.getElementById("mic-btn");
const micIcon = document.getElementById("mic-icon");
const statusText = document.getElementById("status-text");
const statusDot = document.getElementById("status-dot");
const connectionBadge = document.getElementById("connection-badge");
const canvas = document.getElementById("waveform-canvas");
const logContainer = document.getElementById("conversation-log");
const ctx = canvas.getContext("2d");

// ── Audio Modules ───────────────────────────────────────────────────
const streamer = new AudioStreamer();
const player = new AudioPlayer();

// ── App State ───────────────────────────────────────────────────────
let ws = null;
let currentState = State.IDLE;
let animFrameId = null;

// ── WebSocket URL ───────────────────────────────────────────────────
const WS_URL = `ws://${window.location.host}/ws/voice`;

// ── State Transitions ───────────────────────────────────────────────

function setState(newState) {
    currentState = newState;
    updateUI();
}

function updateUI() {
    // Reset classes
    micBtn.classList.remove(
        "state-idle", "state-connecting", "state-listening",
        "state-speaking", "state-error"
    );
    micBtn.classList.add(`state-${currentState}`);

    switch (currentState) {
        case State.IDLE:
            micIcon.textContent = "mic";
            statusText.textContent = "Tap to start conversation";
            statusDot.className = "status-dot offline";
            connectionBadge.textContent = "Disconnected";
            connectionBadge.className = "connection-badge disconnected";
            break;

        case State.CONNECTING:
            micIcon.textContent = "hourglass_top";
            statusText.textContent = "Connecting...";
            statusDot.className = "status-dot connecting";
            connectionBadge.textContent = "Connecting";
            connectionBadge.className = "connection-badge connecting";
            break;

        case State.LISTENING:
            micIcon.textContent = "mic";
            statusText.textContent = "Listening... Speak now";
            statusDot.className = "status-dot online";
            connectionBadge.textContent = "Connected";
            connectionBadge.className = "connection-badge connected";
            break;

        case State.SPEAKING:
            micIcon.textContent = "volume_up";
            statusText.textContent = "Bot is speaking...";
            statusDot.className = "status-dot online";
            connectionBadge.textContent = "Connected";
            connectionBadge.className = "connection-badge connected";
            break;

        case State.ERROR:
            micIcon.textContent = "error_outline";
            statusText.textContent = "Connection error. Tap to retry.";
            statusDot.className = "status-dot offline";
            connectionBadge.textContent = "Error";
            connectionBadge.className = "connection-badge disconnected";
            break;
    }
}

// ── Conversation Log ────────────────────────────────────────────────

function addLogEntry(sender, text) {
    const entry = document.createElement("div");
    entry.className = `log-entry ${sender}`;

    const label = document.createElement("span");
    label.className = "log-label";
    label.textContent = sender === "bot" ? "🤖 Bot" : "🎙️ You";

    const content = document.createElement("span");
    content.className = "log-content";
    content.textContent = text;

    entry.appendChild(label);
    entry.appendChild(content);
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// ── WebSocket Management ────────────────────────────────────────────

async function connect() {
    setState(State.CONNECTING);

    try {
        await player.init();

        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log("[WS] Connected");
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleServerMessage(msg);
        };

        ws.onerror = (err) => {
            console.error("[WS] Error:", err);
            setState(State.ERROR);
        };

        ws.onclose = () => {
            console.log("[WS] Disconnected");
            cleanup();
            setState(State.IDLE);
        };
    } catch (err) {
        console.error("Connection failed:", err);
        setState(State.ERROR);
    }
}

function handleServerMessage(msg) {
    switch (msg.type) {
        case "ready":
            // Session is ready — start microphone and request greeting
            startSession();
            break;

        case "audio":
            // Play audio chunk from Gemini
            if (currentState !== State.SPEAKING) {
                setState(State.SPEAKING);
            }
            player.playChunk(msg.data);
            break;

        case "text":
            // Transcript or text response
            addLogEntry("bot", msg.data);
            break;

        case "turn_complete":
            // Bot finished speaking — go back to listening
            setState(State.LISTENING);
            break;

        case "interrupted":
            // Barge-in detected — bot was interrupted
            player.interrupt();
            setState(State.LISTENING);
            break;

        case "error":
            console.error("[Server Error]", msg.data);
            addLogEntry("bot", `⚠️ Error: ${msg.data}`);
            // Don't disconnect — stay connected for next turn
            if (currentState === State.SPEAKING) {
                setState(State.LISTENING);
            }
            break;

        default:
            console.log("[Server]", msg);
    }
}

async function startSession() {
    try {
        // Start microphone streaming
        await streamer.start(ws);
        setState(State.LISTENING);

        // Request greeting from bot
        ws.send(JSON.stringify({ type: "start" }));

        // Start visualization loop
        startVisualization();
    } catch (err) {
        console.error("Failed to start session:", err);
        addLogEntry("bot", "⚠️ Microphone access denied. Please allow microphone permissions.");
        setState(State.ERROR);
    }
}

async function disconnect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "stop" }));
    }
    cleanup();
    setState(State.IDLE);
}

async function cleanup() {
    stopVisualization();
    await streamer.stop();
    await player.close();
    if (ws) {
        ws.close();
        ws = null;
    }
}

// ── Microphone Button ───────────────────────────────────────────────

micBtn.addEventListener("click", async () => {
    if (currentState === State.IDLE || currentState === State.ERROR) {
        await connect();
    } else {
        await disconnect();
    }
});

// ── Waveform Visualization ──────────────────────────────────────────

function startVisualization() {
    const dpr = window.devicePixelRatio || 1;

    function resize() {
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
    }
    resize();
    window.addEventListener("resize", resize);

    function draw() {
        animFrameId = requestAnimationFrame(draw);

        const width = canvas.width / (window.devicePixelRatio || 1);
        const height = canvas.height / (window.devicePixelRatio || 1);
        ctx.clearRect(0, 0, width, height);

        let data;
        let color;

        if (currentState === State.SPEAKING && player.isPlaying) {
            data = player.getFrequencyData();
            color = getComputedStyle(document.documentElement)
                .getPropertyValue("--accent-speaking").trim() || "#a78bfa";
        } else if (currentState === State.LISTENING) {
            data = streamer.getFrequencyData();
            color = getComputedStyle(document.documentElement)
                .getPropertyValue("--accent-listening").trim() || "#34d399";
        } else {
            // Idle — draw flat line
            ctx.strokeStyle = "rgba(255,255,255,0.1)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, height / 2);
            ctx.lineTo(width, height / 2);
            ctx.stroke();
            return;
        }

        if (!data || data.length === 0) return;

        // Draw frequency bars
        const barCount = Math.min(data.length, 64);
        const barWidth = width / barCount;
        const gap = 2;

        for (let i = 0; i < barCount; i++) {
            const value = data[i] / 255;
            const barHeight = value * height * 0.8;
            const x = i * barWidth;
            const y = (height - barHeight) / 2;

            // Gradient bar
            const gradient = ctx.createLinearGradient(x, y + barHeight, x, y);
            gradient.addColorStop(0, `${color}33`);
            gradient.addColorStop(1, color);

            ctx.fillStyle = gradient;
            ctx.fillRect(x + gap / 2, y, barWidth - gap, barHeight);
        }
    }

    draw();
}

function stopVisualization() {
    if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// ── Keyboard shortcut (Space to toggle) ─────────────────────────────

document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && e.target === document.body) {
        e.preventDefault();
        micBtn.click();
    }
});

// ── Initial State ───────────────────────────────────────────────────
setState(State.IDLE);
