"""Realtime streaming STT service wrapping DashScope's qwen3-asr-flash-realtime.

Built from the official Aliyun SDK reference:
https://help.aliyun.com/zh/model-studio/qwen-asr-realtime-python-sdk

Uses ``dashscope.audio.qwen_omni.OmniRealtimeConversation`` over a persistent
websocket. Audio frames from the pipeline are streamed in as base64 PCM
chunks via ``append_audio``. The SDK's server VAD decides utterance
boundaries and emits interim + final transcripts, which we bridge from the
SDK's background thread onto the asyncio pipeline and push as
``InterimTranscriptionFrame`` / ``TranscriptionFrame``.

Unlike the segmented qwen3-asr-flash service, this one does *not* wait for
the pipeline VAD to chunk utterances; audio is forwarded continuously and
the partial transcript starts appearing while the user is still speaking.
"""

import asyncio
import base64
from collections.abc import AsyncGenerator
from typing import Optional

import dashscope
from dashscope.audio.qwen_omni import (
    MultiModality,
    OmniRealtimeCallback,
    OmniRealtimeConversation,
)
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams
from loguru import logger

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
)
from pipecat.services.settings import STTSettings
from pipecat.services.stt_service import STTService
from pipecat.utils.time import time_now_iso8601
from pipecat.utils.tracing.service_decorators import traced_stt

QWEN_ASR_REALTIME_SAMPLE_RATE = 16000

# Singapore: wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime
QWEN_ASR_REALTIME_URL_CN = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"


class _TranscriptBridgeCallback(OmniRealtimeCallback):
    """Forward SDK events from the websocket thread onto an asyncio queue.

    The SDK calls these methods from a background websocket thread, so every
    queue put must go through ``loop.call_soon_threadsafe``.

    The queue carries 2-tuples: ("interim", text) or ("final", text), plus
    Exception instances on error.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        super().__init__()
        self._loop = loop
        self._queue = queue

    def on_open(self) -> None:
        logger.debug("QwenRealtimeSTT: websocket opened")

    def on_close(self, close_status_code, close_msg) -> None:
        logger.debug(
            f"QwenRealtimeSTT: websocket closed [{close_status_code}] {close_msg}"
        )

    def on_event(self, message: dict) -> None:
        try:
            etype = message["type"]
        except (TypeError, KeyError):
            logger.warning(f"QwenRealtimeSTT: malformed event: {message!r}")
            return

        if etype == "conversation.item.input_audio_transcription.text":
            text = (message.get("text") or message.get("delta") or "").strip()
            if text:
                self._loop.call_soon_threadsafe(
                    self._queue.put_nowait, ("interim", text)
                )
        elif etype == "conversation.item.input_audio_transcription.completed":
            text = (message.get("transcript") or message.get("text") or "").strip()
            if text:
                self._loop.call_soon_threadsafe(
                    self._queue.put_nowait, ("final", text)
                )
        elif etype == "session.created":
            sid = message.get("session", {}).get("id", "?")
            logger.debug(f"QwenRealtimeSTT: session created [{sid}]")
        elif etype == "session.updated":
            logger.debug("QwenRealtimeSTT: session updated")
        elif etype == "input_audio_buffer.speech_started":
            logger.debug("QwenRealtimeSTT: speech started")
        elif etype == "input_audio_buffer.speech_stopped":
            logger.debug("QwenRealtimeSTT: speech stopped")
        elif etype == "session.finished":
            logger.debug("QwenRealtimeSTT: session finished")
        elif etype == "error":
            msg = message.get("error", {}).get("message", str(message))
            logger.error(f"QwenRealtimeSTT: server error: {msg}")
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, RuntimeError(msg)
            )


class QwenRealtimeSTTService(STTService):
    """Streaming speech-to-text via qwen3-asr-flash-realtime over websocket.

    Audio is forwarded continuously to the server, which handles VAD and
    emits interim transcripts while the user speaks plus a final transcript
    when they stop. Pipeline-level VAD (SileroVADAnalyzer on the user
    aggregator) is still used independently for turn detection.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "qwen3-asr-flash-realtime",
        url: str = QWEN_ASR_REALTIME_URL_CN,
        language: str = "en",
        sample_rate: int = QWEN_ASR_REALTIME_SAMPLE_RATE,
        enable_turn_detection: bool = True,
        turn_detection_threshold: float = 0.2,
        turn_detection_silence_duration_ms: int = 600,
        **kwargs,
    ):
        """Initialize the qwen3-asr-flash-realtime STT service.

        Args:
            api_key: DashScope (Aliyun Bailian) API key.
            model: Realtime ASR model name.
            url: Websocket endpoint. Defaults to Beijing.
            language: Language code for the recognizer ("en", "zh", "ja", ...).
            sample_rate: PCM sample rate (16000 or 8000).
            enable_turn_detection: Let the server VAD finalize utterances.
            turn_detection_threshold: Server VAD sensitivity, [-1, 1].
            turn_detection_silence_duration_ms: Silence needed to commit.
            **kwargs: Forwarded to STTService.
        """
        super().__init__(
            sample_rate=sample_rate,
            settings=STTSettings(model=model, language=None),
            **kwargs,
        )

        self._api_key = api_key
        self._model = model
        self._url = url
        self._language = language
        self._enable_turn_detection = enable_turn_detection
        self._turn_detection_threshold = turn_detection_threshold
        self._turn_detection_silence_duration_ms = turn_detection_silence_duration_ms

        self._client: Optional[OmniRealtimeConversation] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue] = None
        self._drain_task: Optional[asyncio.Task] = None

    def can_generate_metrics(self) -> bool:
        return True

    @traced_stt
    async def _handle_transcription(
        self, transcript: str, is_final: bool, language=None
    ):
        """Tracing hook for transcription results."""
        pass

    async def start(self, frame):
        await super().start(frame)
        await self._ensure_connected()

    async def stop(self, frame):
        await super().stop(frame)
        await self._disconnect()

    async def cancel(self, frame):
        await super().cancel(frame)
        await self._disconnect()

    async def cleanup(self):
        await self._disconnect()
        await super().cleanup()

    async def _ensure_connected(self) -> None:
        if self._client is not None:
            return

        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        callback = _TranscriptBridgeCallback(self._loop, self._queue)

        # The SDK reads dashscope.api_key as module-global config.
        dashscope.api_key = self._api_key

        self._client = OmniRealtimeConversation(
            model=self._model,
            callback=callback,
            url=self._url,
        )
        await self._loop.run_in_executor(None, self._client.connect)

        transcription_params = TranscriptionParams(
            language=self._language,
            sample_rate=self.sample_rate,
            input_audio_format="pcm",
        )

        def _update():
            self._client.update_session(
                output_modalities=[MultiModality.TEXT],
                enable_turn_detection=self._enable_turn_detection,
                turn_detection_type="server_vad",
                turn_detection_threshold=self._turn_detection_threshold,
                turn_detection_silence_duration_ms=self._turn_detection_silence_duration_ms,
                enable_input_audio_transcription=True,
                transcription_params=transcription_params,
            )

        await self._loop.run_in_executor(None, _update)
        logger.debug(f"{self}: realtime websocket ready")

        self._drain_task = self.create_task(self._drain_loop())

    async def _disconnect(self) -> None:
        if self._drain_task is not None:
            await self.cancel_task(self._drain_task)
            self._drain_task = None
        if self._client is not None:
            try:
                await self._loop.run_in_executor(None, self._client.close)
            except Exception as e:
                logger.warning(f"{self}: error closing realtime ws: {e}")
            self._client = None

    async def _drain_loop(self) -> None:
        """Drain the bridge queue and push transcription frames downstream."""
        assert self._queue is not None
        while True:
            item = await self._queue.get()
            if isinstance(item, Exception):
                logger.error(f"{self}: realtime STT error: {item}")
                continue
            kind, text = item
            if kind == "interim":
                await self.push_frame(
                    InterimTranscriptionFrame(text, self._user_id, time_now_iso8601())
                )
                await self._handle_transcription(text, False, self._language)
            elif kind == "final":
                logger.debug(f"Transcription: [{text}]")
                await self._handle_transcription(text, True, self._language)
                await self.push_frame(
                    TranscriptionFrame(text, self._user_id, time_now_iso8601())
                )

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        """Forward a PCM chunk to the realtime ASR websocket.

        Transcription frames are pushed asynchronously from ``_drain_loop``
        when the SDK callback fires, so this method yields None.
        """
        if self._client is None:
            await self._ensure_connected()

        audio_b64 = base64.b64encode(audio).decode("ascii")
        client = self._client
        try:
            await self._loop.run_in_executor(
                None, lambda: client.append_audio(audio_b64)
            )
        except Exception as e:
            logger.warning(f"{self}: append_audio failed: {e}")
        yield None
