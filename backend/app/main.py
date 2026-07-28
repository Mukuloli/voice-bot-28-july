"""
FastAPI application — serves the voice bot WebSocket endpoint
and the frontend static files.
No RAG — all knowledge is in the system prompt.
"""

import asyncio
import base64
import json
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.gemini_live import GeminiLiveSession

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ──────────────────────────────────────────────────────
app = FastAPI(
    title="Voice Bot — Mukul Oli Portfolio Assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ────────────────────────────────────────────────────────────
def _get_frontend_dir() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(4):
        candidate = current / "frontend"
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate
        current = current.parent
    return Path(__file__).resolve().parent / "frontend"

_frontend_dir = _get_frontend_dir()
logger.info("Frontend directory resolved to: %s", _frontend_dir)


# ── REST endpoints ───────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the frontend index page."""
    index_path = _frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"status": "error", "message": f"index.html not found at {index_path}"}


@app.get("/api/status")
async def api_status():
    """Return health and config info."""
    return {
        "status": "ok",
        "model": settings.gemini_model,
        "voice": settings.voice_name,
    }


# ── Static files (frontend assets) ──────────────────────────────────
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")


# ── WebSocket voice endpoint ────────────────────────────────────────

@app.websocket("/ws/voice")
async def voice_websocket(ws: WebSocket):
    """
    Bidirectional voice streaming endpoint.

    Client sends JSON messages:
        {"type": "audio", "data": "<base64 PCM 16kHz>"}
        {"type": "start"}       — request greeting
        {"type": "stop"}        — end session

    Server sends JSON messages:
        {"type": "audio", "data": "<base64 PCM 24kHz>"}
        {"type": "text",  "data": "<transcript>"}
        {"type": "turn_complete"}
        {"type": "interrupted"}
        {"type": "error", "data": "<message>"}
        {"type": "ready"}
    """
    await ws.accept()
    logger.info("Client connected via WebSocket.")

    gemini = GeminiLiveSession()

    try:
        # Connect to Gemini Live API
        await gemini.connect()
        await ws.send_json({"type": "ready"})

        # Start concurrent tasks
        receive_task = asyncio.create_task(
            _gemini_to_client(gemini, ws)
        )
        send_task = asyncio.create_task(
            _client_to_gemini(ws, gemini)
        )

        # Wait for client loop to finish (disconnect or stop request)
        try:
            await send_task
        finally:
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info("Client disconnected.")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await ws.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
    finally:
        await gemini.close()
        logger.info("Session cleaned up.")


async def _client_to_gemini(ws: WebSocket, gemini: GeminiLiveSession):
    """Forward client messages to Gemini."""
    try:
        while gemini.is_active:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "audio":
                # Decode base64 PCM and forward to Gemini
                audio_bytes = base64.b64decode(msg["data"])
                await gemini.send_audio(audio_bytes)

            elif msg_type == "start":
                # Trigger the greeting
                await gemini.send_text(
                    "Please greet the user now. This is the start of the conversation."
                )

            elif msg_type == "stop":
                logger.info("Client requested stop.")
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected (send loop).")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Error in client→Gemini loop: %s", e)


async def _gemini_to_client(gemini: GeminiLiveSession, ws: WebSocket):
    """Forward Gemini responses to the client."""
    try:
        async for response in gemini.receive_responses():
            try:
                await ws.send_json(response)
            except Exception as send_err:
                logger.error("Failed to send to client WS: %s", send_err)
                break
        logger.warning("Gemini receive_responses() generator ended.")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Error in Gemini→client loop: %s", e)


# ── Run with: uvicorn app.main:app --reload ──────────────────────────
