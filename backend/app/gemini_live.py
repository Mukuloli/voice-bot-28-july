"""
Gemini Live API session manager.

Manages a bidirectional WebSocket session with Gemini's Live API
for native speech-to-speech voice interaction.
No RAG — all knowledge is embedded in the system instruction.
"""

import asyncio
import base64
import logging
from typing import AsyncGenerator

from google import genai
from google.genai import types

from app.config import settings
from app.prompts import SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)


class GeminiLiveSession:
    """
    Wraps a Gemini Live API session, handling audio streaming
    and lifecycle management.
    """

    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._cm = None
        self._session = None
        self._is_active = False

    async def connect(self) -> None:
        """Establish a live session with Gemini."""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=settings.voice_name,
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=SYSTEM_INSTRUCTION)]
            ),
        )

        self._cm = self._client.aio.live.connect(
            model=settings.gemini_model,
            config=config,
        )
        self._session = await self._cm.__aenter__()
        self._is_active = True
        logger.info("Gemini Live session connected (model=%s)", settings.gemini_model)

    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send raw PCM audio data to the Gemini session.

        Args:
            audio_data: Raw 16-bit PCM audio at 16kHz, little-endian.
        """
        if not self._session or not self._is_active:
            return

        try:
            await self._session.send_realtime_input(
                audio=types.Blob(
                    data=audio_data,
                    mime_type="audio/pcm;rate=16000",
                )
            )
        except Exception as e:
            logger.error("Error sending audio to Gemini: %s", e)

    async def send_text(self, text: str) -> None:
        """Send a text message to trigger a response (e.g., greeting)."""
        if not self._session or not self._is_active:
            return

        try:
            await self._session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=text)],
                ),
                turn_complete=True,
            )
            logger.info("Text sent to Gemini: %s", text[:80])
        except Exception as e:
            logger.error("Error sending text to Gemini: %s", e)

    async def receive_responses(self) -> AsyncGenerator[dict, None]:
        """
        Async generator that yields responses from the Gemini session.

        Yields dicts with one of:
          - {"type": "audio", "data": "<base64 pcm>"}
          - {"type": "text", "data": "<text content>"}
          - {"type": "turn_complete"}
          - {"type": "interrupted"}
          - {"type": "error", "data": "<error message>"}
        """
        if not self._session:
            return

        try:
            while self._is_active:
                async for response in self._session.receive():
                    # ── Server content (audio / text) ──────────────
                    if response.server_content is not None:
                        sc = response.server_content

                        # Check for turn completion
                        if sc.turn_complete:
                            logger.debug("Turn complete.")
                            yield {"type": "turn_complete"}
                            continue

                        # Check for interruption
                        if sc.interrupted:
                            logger.debug("Interrupted by user.")
                            yield {"type": "interrupted"}
                            continue

                        # Process model turn parts
                        if sc.model_turn and sc.model_turn.parts:
                            for part in sc.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    audio_b64 = base64.b64encode(
                                        part.inline_data.data
                                    ).decode("ascii")
                                    yield {"type": "audio", "data": audio_b64}
                                elif part.text:
                                    yield {"type": "text", "data": part.text}

                # If receive() iterator ends for a turn, sleep briefly and wait for next turn
                logger.info("Gemini turn receive finished, waiting for next turn...")
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Receive loop cancelled.")
        except Exception as e:
            logger.error("Error in receive loop: %s", e)
            yield {"type": "error", "data": str(e)}

    async def close(self) -> None:
        """Cleanly close the Gemini session."""
        self._is_active = False
        if self._cm:
            try:
                await self._cm.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing Gemini session: %s", e)
            self._cm = None
            self._session = None
        logger.info("Gemini Live session closed.")

    @property
    def is_active(self) -> bool:
        return self._is_active
