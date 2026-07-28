# 🎙️ AI Voice Bot — Mukul Oli's Portfolio Assistant

A production-ready, real-time AI voice bot that acts as a personal portfolio assistant. Built with **Gemini Live API** for native speech-to-speech, **FAISS-powered RAG** for knowledge grounding, and a premium dark-themed web interface.

## ✨ Features

- **Real-Time Voice Conversation** — Native speech-to-speech via Gemini Live API
- **RAG Knowledge Base** — Answers grounded in resume/portfolio data using FAISS vector search
- **Barge-In Support** — Interrupt the bot mid-sentence; it stops and listens immediately
- **Noise Cancellation** — Browser-level echo cancellation and noise suppression
- **Low Latency** — WebSocket streaming with AudioWorklet for minimal delay
- **Premium UI** — Dark glassmorphism theme with animated waveform visualization
- **Conversation Memory** — Multi-turn context maintained by Gemini Live session

## 🏗️ Architecture

```
Browser                          Backend                    Gemini
┌──────────┐    WebSocket    ┌──────────────┐    SDK     ┌─────────────┐
│ AudioWork│───────────────→ │  FastAPI WS  │──────────→ │ Live API    │
│ let 16kHz│                 │  Proxy       │            │ (Audio I/O) │
│          │← ─ ─ ─ ─ ─ ─ ─ │              │← ─ ─ ─ ─ ─│             │
│ Player   │  Audio 24kHz    │  RAG Engine  │  Tool Call │ Function    │
│ 24kHz    │                 │  (FAISS)     │←──────────→│ Calling     │
└──────────┘                 └──────────────┘            └─────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [Gemini API key](https://aistudio.google.com/apikey)

### 1. Clone & Setup

```bash
cd voice-bot-28/backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example env file
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux

# Edit .env and add your Gemini API key
```

### 3. Run the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. Open the App

Navigate to **http://localhost:8000** in your browser.

Click the microphone button to start talking!

## 📁 Project Structure

```
voice-bot-28/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + WebSocket endpoint
│   │   ├── gemini_live.py       # Gemini Live API session manager
│   │   ├── config.py            # Settings & environment variables
│   │   ├── prompts.py           # System instructions & tool declarations
│   │   └── rag/
│   │       ├── knowledge_base.py  # FAISS vector store builder
│   │       └── retriever.py       # Similarity search
│   ├── data/
│   │   └── portfolio.md         # Your resume/portfolio content
│   ├── vectorstore/             # Auto-generated FAISS index
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/
│   │   ├── app.js               # Main controller
│   │   ├── audio-streamer.js    # Microphone capture
│   │   └── audio-player.js     # Audio playback
│   └── worklet/
│       └── pcm-processor.js    # AudioWorklet for PCM conversion
└── README.md
```

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Your Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash-preview-native-audio-dialog` | Gemini Live API model |
| `VOICE_NAME` | `Kore` | Voice: Puck, Charon, Kore, Fenrir, Aoede |

## 📝 Customizing the Knowledge Base

Edit `backend/data/portfolio.md` with your real resume and portfolio content. The vector store rebuilds automatically on server restart when it detects changes.

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, WebSockets
- **AI:** Gemini Live API (google-genai SDK)
- **RAG:** LangChain, FAISS, Google Embeddings
- **Frontend:** HTML5, CSS3, JavaScript (ES Modules)
- **Audio:** Web Audio API, AudioWorklet

## 📄 License

MIT
