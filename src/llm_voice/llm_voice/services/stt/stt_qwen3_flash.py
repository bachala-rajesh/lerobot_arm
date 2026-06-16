#
# Custom Pipecat STT service wrapping Alibaba DashScope's qwen3-asr-flash.
#
# Uses dashscope.MultiModalConversation.call(...) -- the synchronous HTTP
# variant. The response natively carries an `emotion` annotation alongside
# the transcript, which we surface as a separate EmotionFrame for the
# expressive-lamp loop.
#
# Docs: https://www.alibabacloud.com/help/en/model-studio/qwen-asr-api-reference
#

import asyncio
import base64
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import dashscope
from loguru import logger

from pipecat.frames.frames import DataFrame, ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.settings import STTSettings
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.utils.time import time_now_iso8601
from pipecat.utils.tracing.service_decorators import traced_stt

# SegmentedSTTService uses this rate when wrapping the VAD buffer into WAV.
QWEN_ASR_SAMPLE_RATE = 16000

# qwen3-asr-flash hard cap per request.
MAX_AUDIO_BYTES = 10 * 1024 * 1024


@dataclass
class EmotionFrame(DataFrame):
    """Vocal emotion detected on the user's last utterance.

    Emitted by STT services that surface affect annotations. Travels
    through the pipeline as opaque data -- context aggregators and TTS
    services do not consume it. Downstream consumers (e.g. an expressive-
    lamp controller) filter for this frame type.

    Parameters:
        emotion: One of "surprised", "neutral", "happy", "sad",
            "disgusted", "angry", "fearful" (qwen3-asr-flash set).
        source: Identifier for the producer of the emotion label, so
            consumers can disambiguate when multiple emotion sources
            are wired into the same pipeline.
    """

    emotion: str
    source: str = "qwen3-asr-flash"

    def __str__(self):
        return f"{self.name}(emotion: {self.emotion}, source: {self.source})"


def _deep_get(obj, *path):
    """Walk a path through nested objects, dicts, and lists.

    Integer path elements are treated as list indices; everything else is
    tried as a dict key, then as an attribute. Returns None as soon as any
    step is missing, so callers can chain long paths without try/except.
    """
    for key in path:
        if obj is None:
            return None
        if isinstance(key, int):
            obj = obj[key] if isinstance(obj, list) and 0 <= key < len(obj) else None
        elif isinstance(obj, dict):
            obj = obj.get(key)
        else:
            obj = getattr(obj, key, None)
    return obj


class Qwen3FlashSTTService(SegmentedSTTService):
    """Speech-to-text via Alibaba DashScope's qwen3-asr-flash (sync HTTP).

    Inherits from SegmentedSTTService so each VAD-delimited utterance is
    handed to us as a complete WAV blob. We base64-encode the whole WAV
    inline as a data URI; the blocking DashScope call runs on an executor
    thread and the single response is delivered back to the event loop
    through a queue so the pipeline never stalls.

    Per turn this service yields a TranscriptionFrame, and -- if the
    response carries an emotion annotation -- an EmotionFrame after it.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "qwen3-asr-flash",
        language: str = "en",
        system_message: str = "",
        stream: bool = True,
        enable_itn: bool = True,
        sample_rate: int = QWEN_ASR_SAMPLE_RATE,
        **kwargs,
    ):
        """Initialize the qwen3-asr-flash STT service.

        Args:
            api_key: DashScope (Aliyun Bailian) API key.
            model: ASR model name. Default "qwen3-asr-flash".
            language: Language code to bias toward, e.g. "en", "zh".
                Pass "" to let the model auto-detect.
            system_message: Optional context-biasing prompt (10k-token
                cap server-side). Sent as a system message only when
                non-empty.
            enable_itn: Inverse text normalization (digits/punctuation
                in Chinese/English transcripts).
            sample_rate: Input sample rate. SegmentedSTTService uses
                this to frame the buffered PCM into a WAV.
            stream: Whether to stream the response or not. Default True.
                If False, the response is returned as a single frame.
            **kwargs: Forwarded to SegmentedSTTService.
        """
        # language=None on the settings object: qwen3-asr-flash takes a
        # raw code via asr_options, not via the base class's Language
        # enum, so we don't want the enum coercion to run.
        super().__init__(
            sample_rate=sample_rate,
            settings=STTSettings(model=model, language=None),
            **kwargs,
        )

        self._api_key = api_key
        self._model = model
        self._language = language
        self._system_message = system_message
        self._enable_itn = enable_itn
        self._stream = stream

    def can_generate_metrics(self) -> bool:
        """Indicate that this service supports TTFB and usage metrics."""
        return True

    @traced_stt
    async def _handle_transcription(
        self, transcript: str, is_final: bool, language=None
    ):
        """Tracing hook for transcription results."""
        pass

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        """Transcribe a single VAD-delimited utterance via qwen3-asr-flash.

        Args:
            audio: Complete WAV file (header + 16-bit mono PCM at
                self.sample_rate) produced by SegmentedSTTService.

        Yields:
            TranscriptionFrame followed by EmotionFrame on success, or a
            single ErrorFrame on failure. No frames if the response text
            is empty (e.g. silence-only segment).
        """
        await self.start_processing_metrics()

        if len(audio) > MAX_AUDIO_BYTES:
            logger.error(
                f"{self}: audio exceeds 10 MB cap ({len(audio)} bytes), dropping"
            )
            await self.stop_processing_metrics()
            yield ErrorFrame(error="Qwen STT audio exceeds 10 MB cap")
            return

        # qwen3-asr-flash accepts the whole WAV inline; no header stripping.
        audio_b64 = base64.b64encode(audio).decode("ascii")
        audio_uri = f"data:audio/wav;base64,{audio_b64}"

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()

        def _produce():
            """Run the blocking DashScope sync call in a worker thread.

            Exactly one response (or a terminal exception) is handed back
            to the event loop via the queue, then SENTINEL marks the end.
            """
            messages = []
            if self._system_message:
                messages.append({
                    "role": "system",
                    "content": [{"text": self._system_message}],
                })
            messages.append({
                "role": "user",
                "content": [{"audio": audio_uri}],
            })

            asr_options = {"enable_itn": self._enable_itn}
            if self._language:
                asr_options["language"] = self._language

            try:
                for response in dashscope.MultiModalConversation.call(
                    api_key=self._api_key,
                    model=self._model,
                    messages=messages,
                    result_format="message",
                    asr_options=asr_options,
                    stream=self._stream,
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, response)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

        producer = loop.run_in_executor(None, _produce)

        response = None
        try:
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break
                if isinstance(item, Exception):
                    raise item
                response = item
        except Exception as e:
            logger.error(f"{self}: Qwen STT error: {e}")
            await self.stop_processing_metrics()
            await producer
            yield ErrorFrame(error=f"Qwen STT error: {e}")
            return
        finally:
            # On the happy path the worker is already done; this just
            # guarantees a clean unwind on the error path too.
            await producer

        await self.stop_processing_metrics()

        # Response shape (confirmed via the qwen-asr-api-reference docs):
        #   output.choices[0].message.content[0].text
        #   output.choices[0].message.annotations[0].emotion
        text = _deep_get(
            response, "output", "choices", 0, "message", "content", 0, "text"
        ) or ""
        emotion = _deep_get(
            response, "output", "choices", 0, "message", "annotations", 0, "emotion"
        ) or ""
        text = text.strip()

        if not text:
            # Silence segment or filtered output -- don't push empty frames.
            return

        await self._handle_transcription(text, True, None)
        logger.debug(f"Transcription: [{text}] emotion: [{emotion}]")

        yield TranscriptionFrame(text, self._user_id, time_now_iso8601())
        if emotion:
            yield EmotionFrame(emotion=emotion)
