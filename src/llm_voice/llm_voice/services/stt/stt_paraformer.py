#
# Custom Pipecat STT service wrapping Alibaba DashScope's Paraformer ASR.
#
# Uses ``dashscope.audio.asr.Recognition`` in streaming mode with the
# ``paraformer-realtime-v2`` model. The model accepts ``language_hints`` so
# we can bias recognition toward English without disabling multilingual
# fallback (useful for accented speakers).
#

import asyncio
import io
import wave
from collections.abc import AsyncGenerator

from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.settings import STTSettings
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.utils.time import time_now_iso8601
from pipecat.utils.tracing.service_decorators import traced_stt

# Paraformer-realtime-v2 supports 16 kHz mono PCM input.
SAMPLE_RATE = 16000


class ParaformerSTTService(SegmentedSTTService):
    """Speech-to-text using Alibaba DashScope's Paraformer ASR.

    Inherits from ``SegmentedSTTService`` so each VAD-delimited utterance is
    handed to us as a single WAV blob. We strip the WAV header, then stream
    the raw PCM into the DashScope Recognition session in small chunks and
    collect the resulting sentences. The blocking DashScope worker thread is
    bridged to the asyncio event loop through a queue so the pipeline never
    stalls.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "paraformer-realtime-v2",
        language_hints: tuple[str, ...] = ("en",),
        sample_rate: int = SAMPLE_RATE,
        **kwargs,
    ):
        """Initialize the Qwen / Paraformer STT service.

        Args:
            api_key: DashScope (Aliyun Bailian) API key.
            model: ASR model. ``paraformer-realtime-v2`` is multilingual and
                supports ``language_hints``.
            language_hints: Languages to bias recognition toward, e.g.
                ``("en",)`` or ``("zh", "en")``. Only honored by
                paraformer-realtime-v2.
            sample_rate: Input sample rate. Paraformer-realtime-v2 expects
                16 kHz mono.
            **kwargs: Forwarded to the base SegmentedSTTService.
        """
        # language=None here because Paraformer's multilingual mode is
        # configured via language_hints, not the single-language settings
        # field. Storing None avoids the base class's Language enum coercion.
        super().__init__(
            sample_rate=sample_rate,
            settings=STTSettings(model=model, language=None),
            **kwargs,
        )

        self._api_key = api_key
        self._model = model
        self._language_hints = list(language_hints)

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
        """Transcribe a single VAD-delimited utterance via Paraformer.

        Args:
            audio: Complete WAV file (with header) produced by
                ``SegmentedSTTService``. 16-bit mono PCM at ``self.sample_rate``.

        Yields:
            TranscriptionFrame with the concatenated final sentences, or
            ErrorFrame if Paraformer returned an error.
        """
        await self.start_processing_metrics()

        # SegmentedSTTService wraps the audio in a WAV container; Paraformer's
        # streaming PCM mode wants the raw samples, so unwrap here.
        try:
            with wave.open(io.BytesIO(audio), "rb") as wav:
                pcm = wav.readframes(wav.getnframes())
        except wave.Error as e:
            logger.error(f"{self}: failed to parse WAV: {e}")
            await self.stop_processing_metrics()
            yield ErrorFrame(error=f"Qwen STT WAV parse error: {e}")
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()

        class _Callback(RecognitionCallback):
            """Marshal DashScope callbacks (worker-thread) back to the event loop.

            ``on_event`` may fire many times per utterance with partial
            transcripts; we only forward the finalized sentences (those with
            an ``end_time``) since the pipeline wants one TranscriptionFrame
            per turn.
            """

            def on_event(_self, result: RecognitionResult) -> None:
                sentence = result.get_sentence()
                if isinstance(sentence, dict) and RecognitionResult.is_sentence_end(
                    sentence
                ):
                    text = sentence.get("text", "")
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)

            def on_complete(_self) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

            def on_error(_self, result: RecognitionResult) -> None:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    RuntimeError(f"Paraformer error: {result.message}"),
                )

            def on_close(_self) -> None:
                # Belt-and-suspenders: in case on_complete didn't fire.
                loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

        # 100 ms of audio per send: sample_rate * 2 bytes/sample / 10.
        chunk_size = self.sample_rate * 2 // 10

        def _produce():
            """Drive the blocking Recognition session in a worker thread.

            ``Recognition.start()`` spawns its own internal worker thread that
            invokes our callbacks. ``stop()`` waits for that worker to drain,
            so by the time we exit the try block all sentences have been
            queued.
            """
            try:
                recognition = Recognition(
                    model=self._model,
                    format="pcm",
                    sample_rate=self.sample_rate,
                    callback=_Callback(),
                    api_key=self._api_key,
                    language_hints=self._language_hints,
                )
                recognition.start()
                for i in range(0, len(pcm), chunk_size):
                    recognition.send_audio_frame(pcm[i : i + chunk_size])
                recognition.stop()
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

        producer = loop.run_in_executor(None, _produce)

        sentences: list[str] = []
        try:
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break
                if isinstance(item, Exception):
                    raise item
                sentences.append(item)
        except Exception as e:
            logger.error(f"{self}: Qwen STT error: {e}")
            await self.stop_processing_metrics()
            await producer  # let the worker unwind before we return
            yield ErrorFrame(error=f"Qwen STT error: {e}")
            return
        finally:
            # Make sure the executor task has fully unwound; on the happy
            # path it's already done by the time we get here.
            await producer

        await self.stop_processing_metrics()

        text = " ".join(sentences).strip()
        if text:
            await self._handle_transcription(text, True, None)
            logger.debug(f"Transcription: [{text}]")
            yield TranscriptionFrame(
                text,
                self._user_id,
                time_now_iso8601(),
            )
