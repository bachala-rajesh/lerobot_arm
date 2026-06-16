"""Realtime TTS service wrapping DashScope's qwen3-tts-flash-realtime.

Uses ``dashscope.audio.qwen_tts_realtime.QwenTtsRealtime`` over a persistent
WebSocket so time-to-first-audio is lower than the non-realtime HTTP variant.
The DashScope SDK delivers audio chunks via synchronous callbacks on a
background thread; we bridge those to the asyncio pipeline through a queue.
"""

import asyncio
import base64
from collections.abc import AsyncGenerator
from typing import Optional

import dashscope
from dashscope.audio.qwen_tts_realtime import (
    AudioFormat,
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
)
from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts

from llm_voice.frames.tts_instruction_update_frames import TTSInstructionUpdateFrame

QWEN_TTS_REALTIME_SAMPLE_RATE = 24000

# Singapore: wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime
QWEN_TTS_REALTIME_URL_CN = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"

# Sentinel objects shipped through the audio queue to mark end-of-response.
_RESPONSE_DONE = object()


class _AudioBridgeCallback(QwenTtsRealtimeCallback):
    """Forward SDK events from the websocket thread onto an asyncio queue.

    The SDK calls these methods from a background websocket thread, so every
    queue put must go through ``loop.call_soon_threadsafe``.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        super().__init__()
        self._loop = loop
        self._queue = queue

    def on_open(self) -> None:
        logger.debug("QwenRealtimeTTS: websocket opened")

    def on_close(self, close_status_code, close_msg) -> None:
        logger.debug(
            f"QwenRealtimeTTS: websocket closed [{close_status_code}] {close_msg}"
        )

    def on_error(self, error) -> None:
        logger.error(f"QwenRealtimeTTS: ws error: {error}")
        self._loop.call_soon_threadsafe(
            self._queue.put_nowait, RuntimeError(str(error))
        )

    def on_event(self, response) -> None:
        try:
            etype = response["type"]
        except (TypeError, KeyError):
            logger.warning(f"QwenRealtimeTTS: malformed event: {response!r}")
            return

        if etype == "response.audio.delta":
            audio_b64 = response.get("delta", "")
            if audio_b64:
                pcm = base64.b64decode(audio_b64)
                self._loop.call_soon_threadsafe(self._queue.put_nowait, pcm)
        elif etype == "response.done":
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, _RESPONSE_DONE
            )
        elif etype == "session.created":
            sid = response.get("session", {}).get("id", "?")
            logger.debug(f"QwenRealtimeTTS: session created [{sid}]")
        elif etype == "session.finished":
            logger.debug("QwenRealtimeTTS: session finished")
        elif etype == "error":
            msg = response.get("error", {}).get("message", str(response))
            logger.error(f"QwenRealtimeTTS: server error: {msg}")
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, RuntimeError(msg)
            )


class QwenRealtimeTTSService(TTSService):
    """Text-to-speech using qwen3-tts-flash-realtime over a websocket.

    The websocket connection is opened lazily on the first ``run_tts`` call
    and reused for the rest of the session. Each utterance issues an
    ``update_session`` (to apply the current instructions), streams the text
    via ``append_text`` / ``finish``, and yields PCM audio frames until the
    server emits ``response.done``.
    """

    def __init__(
        self,
        *,
        api_key: str,
        voice: str = "Cherry",
        model: str = "qwen3-tts-flash-realtime",
        url: str = QWEN_TTS_REALTIME_URL_CN,
        instructions: str = "",
        sample_rate: int = QWEN_TTS_REALTIME_SAMPLE_RATE,
        **kwargs,
    ):
        super().__init__(
            sample_rate=sample_rate,
            push_start_frame=True,
            push_stop_frames=True,
            settings=TTSSettings(model=model, voice=voice, language=None),
            **kwargs,
        )
        self._api_key = api_key
        self._voice = voice
        self._model = model
        self._url = url
        self._instructions = instructions

        self._client: Optional[QwenTtsRealtime] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue] = None

    def can_generate_metrics(self) -> bool:
        return True

    def set_emotion(self, instruction: str) -> None:
        """Update the delivery instructions for the next utterance."""
        logger.debug(f"{self}: setting emotion [{instruction[:60]}...]")
        self._instructions = instruction

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Consume instruction-update control frames in FIFO order with text
        # frames so the instructions used for each synthesis match the text
        # that follows.
        if isinstance(frame, TTSInstructionUpdateFrame):
            self._instructions = frame.instructions
            logger.debug(f"{self}: instructions updated via control frame")
            return
        await super().process_frame(frame, direction)

    async def _ensure_connected(self) -> None:
        if self._client is not None:
            return

        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        callback = _AudioBridgeCallback(self._loop, self._queue)

        # The SDK reads dashscope.api_key as module-global config.
        dashscope.api_key = self._api_key

        self._client = QwenTtsRealtime(
            model=self._model,
            callback=callback,
            url=self._url,
        )
        # connect() blocks until the websocket handshake completes; offload.
        await self._loop.run_in_executor(None, self._client.connect)
        logger.debug(f"{self}: realtime websocket ready")

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        logger.debug(f"{self}: realtime TTS [{text}]")
        await self._ensure_connected()
        await self.start_tts_usage_metrics(text)

        session_kwargs = dict(
            voice=self._voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode="server_commit",
        )
        if self._instructions:
            session_kwargs["instructions"] = self._instructions
            session_kwargs["optimize_instructions"] = True

        client = self._client
        loop = self._loop

        # SDK calls are blocking from asyncio's perspective; offload them.
        await loop.run_in_executor(
            None, lambda: client.update_session(**session_kwargs)
        )
        await loop.run_in_executor(None, lambda: client.append_text(text))
        await loop.run_in_executor(None, client.finish)

        try:
            while True:
                item = await self._queue.get()
                if item is _RESPONSE_DONE:
                    break
                if isinstance(item, Exception):
                    raise item

                await self.stop_ttfb_metrics()
                yield TTSAudioRawFrame(
                    audio=item,
                    sample_rate=self.sample_rate,
                    num_channels=1,
                    context_id=context_id,
                )
        except Exception as e:
            logger.error(f"{self}: realtime TTS error: {e}")
            yield ErrorFrame(error=f"Realtime TTS error: {e}")
        finally:
            await self.stop_ttfb_metrics()

    async def cleanup(self):
        if self._client is not None:
            try:
                await self._loop.run_in_executor(None, self._client.close)
            except Exception as e:
                logger.warning(f"{self}: error closing realtime ws: {e}")
            self._client = None
        await super().cleanup()
