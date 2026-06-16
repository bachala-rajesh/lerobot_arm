"""V2 realtime TTS service wrapping DashScope's qwen3-tts-flash-realtime.

Built from the official Aliyun SDK reference:
https://help.aliyun.com/zh/model-studio/qwen-tts-realtime-python-sdk

Differences from the v1 service (tts_qwen3_flash_realtime.py):
- Exposes the full SDK session knobs: language_type, speech_rate,
  pitch_rate, volume, optimize_instructions.
- Per-utterance overrides via TTSInstructionUpdateFrame still supported.
- Same lazy-connect + asyncio-queue bridge pattern.
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

# Sentinel shipped through the audio queue to mark end-of-response.
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
        logger.debug("QwenRealtimeTTSv2: websocket opened")

    def on_close(self, close_status_code, close_msg) -> None:
        logger.debug(
            f"QwenRealtimeTTSv2: websocket closed [{close_status_code}] {close_msg}"
        )

    def on_error(self, error) -> None:
        logger.error(f"QwenRealtimeTTSv2: ws error: {error}")
        self._loop.call_soon_threadsafe(
            self._queue.put_nowait, RuntimeError(str(error))
        )

    def on_event(self, response) -> None:
        try:
            etype = response["type"]
        except (TypeError, KeyError):
            logger.warning(f"QwenRealtimeTTSv2: malformed event: {response!r}")
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
            logger.debug(f"QwenRealtimeTTSv2: session created [{sid}]")
        elif etype == "session.finished":
            logger.debug("QwenRealtimeTTSv2: session finished")
        elif etype == "error":
            msg = response.get("error", {}).get("message", str(response))
            logger.error(f"QwenRealtimeTTSv2: server error: {msg}")
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, RuntimeError(msg)
            )


class QwenRealtimeTTSServiceV2(TTSService):
    """Text-to-speech via qwen3-tts-flash-realtime over websocket (v2).

    All session knobs from the official SDK are exposed as constructor args
    and applied on each ``run_tts`` call. The instructions field can also be
    updated mid-pipeline via TTSInstructionUpdateFrame (used by the emotion
    tag processor).
    """

    def __init__(
        self,
        *,
        api_key: str,
        voice: str = "Cherry",
        model: str = "qwen3-tts-flash-realtime",
        url: str = QWEN_TTS_REALTIME_URL_CN,
        language_type: str = "Auto",
        instructions: str = "",
        optimize_instructions: bool = True,
        speech_rate: float = 1.0,
        pitch_rate: float = 1.0,
        volume: int = 50,
        mode: str = "commit",
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
        self._language_type = language_type
        self._instructions = instructions
        self._optimize_instructions = optimize_instructions
        self._speech_rate = speech_rate
        self._pitch_rate = pitch_rate
        self._volume = volume
        self._mode = mode

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

    def _build_session_kwargs(self) -> dict:
        kwargs = dict(
            voice=self._voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            language_type=self._language_type,
            mode=self._mode,
            speech_rate=self._speech_rate,
            pitch_rate=self._pitch_rate,
            volume=self._volume,
        )
        if self._instructions:
            kwargs["instructions"] = self._instructions
            kwargs["optimize_instructions"] = self._optimize_instructions
        return kwargs

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        logger.debug(f"{self}: realtime TTS [{text}]")
        await self._ensure_connected()
        await self.start_tts_usage_metrics(text)

        client = self._client
        loop = self._loop
        session_kwargs = self._build_session_kwargs()

        # SDK calls are blocking from asyncio's perspective; offload them.
        await loop.run_in_executor(
            None, lambda: client.update_session(**session_kwargs)
        )
        await loop.run_in_executor(None, lambda: client.append_text(text))
        # Use commit() not finish(); finish() closes the websocket and would
        # break every subsequent run_tts call.
        await loop.run_in_executor(None, client.commit)

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
