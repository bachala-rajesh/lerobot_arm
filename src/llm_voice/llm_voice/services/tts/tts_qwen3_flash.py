#
# Custom Pipecat TTS service wrapping Alibaba DashScope's Qwen3 TTS.
#
# Uses dashscope.MultiModalConversation.call(stream=True, ...) with the
# "qwen3-tts-instruct-flash" model so we can steer delivery with natural-
# language `instructions` (e.g. "speak excitedly").
#

import asyncio
import base64
from collections.abc import AsyncGenerator

import dashscope
from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts

from llm_voice.frames.tts_instruction_update_frames import TTSInstructionUpdateFrame

# Qwen3 TTS streaming returns raw 24 kHz mono 16-bit PCM.
QWEN_TTS_SAMPLE_RATE = 24000


def _deep_get(obj, *path):
    """Walk a path through nested objects, trying attribute then key access.

    DashScope responses sometimes expose fields as attributes
    (`chunk.output.audio.data`) and sometimes as dict keys. This handles both
    and returns None if any step is missing.
    """
    for key in path:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            obj = getattr(obj, key, None)
    return obj


class QwenTTSService(TTSService):
    """Text-to-speech using Alibaba DashScope's Qwen3 TTS (instruct) model.

    Streams audio over HTTP via ``dashscope.MultiModalConversation.call``. The
    blocking DashScope generator is consumed in a worker thread and bridged to
    the asyncio event loop through a queue so the pipeline never stalls.
    """

    def __init__(
        self,
        *,
        api_key: str,
        voice: str = "Cherry",
        model: str = "qwen3-tts-instruct-flash",
        language_type: str = "English",
        instructions: str = "",
        sample_rate: int = QWEN_TTS_SAMPLE_RATE,
        **kwargs,
    ):
        """Initialize the Qwen3 TTS service.

        Args:
            api_key: DashScope (Aliyun Bailian) API key.
            voice: Qwen voice name (e.g. "Cherry").
            model: TTS model. Use "qwen3-tts-instruct-flash" for instruction control.
            language_type: Hint for pronunciation/intonation (e.g. "English", "Chinese").
            instructions: Natural-language delivery instructions (emotion/style).
                Sent only when non-empty, alongside optimize_instructions=True.
            sample_rate: Output sample rate. Qwen3 TTS emits 24000 Hz PCM.
            **kwargs: Forwarded to the base TTSService.
        """
        # The base class always holds a store-mode TTSSettings and validates
        # that every field is set. We drive voice/model ourselves, so populate
        # them here; language=None marks it as not driven via settings (Qwen
        # uses its own language_type string instead).
        # push_start_frame / push_stop_frames let the base class emit
        # TTSStartedFrame, TTSStoppedFrame, create the audio context, and
        # start TTFB metrics around our run_tts. We only yield audio.
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
        self._language_type = language_type
        self._instructions = instructions

    def can_generate_metrics(self) -> bool:
        """Indicate that this service supports TTFB and usage metrics."""
        return True

    def set_emotion(self, instruction: str):
        """Update the delivery instructions mid-conversation.

        Takes effect on the next ``run_tts`` call. Pass an empty string to turn
        instruction control off.

        Args:
            instruction: Natural-language style/emotion guidance.
        """
        logger.debug(f"{self}: setting emotion instructions [{instruction}]")
        self._instructions = instruction

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Consume TTSInstructionUpdateFrame in FIFO order with the surrounding
        # text frames so the instructions used by run_tts always match the
        # text that immediately follows. Anything else is handled by the base.
        if isinstance(frame, TTSInstructionUpdateFrame):
            self._instructions = frame.instructions
            logger.debug(
                f"{self}: instructions updated via control frame "
                f"[{frame.instructions[:60]}...]"
            )
            return
        await super().process_frame(frame, direction)

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        """Synthesize speech from text using Qwen3 TTS streaming.

        Args:
            text: The text to synthesize.
            context_id: Unique identifier for this TTS context.

        Yields:
            TTSAudioRawFrame chunks of 24 kHz mono PCM audio.
        """
        logger.debug(f"{self}: Generating TTS [{text}]")

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()

        def _produce():
            """Run the blocking DashScope generator in a worker thread.

            Each streamed chunk (or a terminal exception) is handed back to the
            event loop via the asyncio queue; SENTINEL marks the end.
            """
            try:
                call_kwargs = dict(
                    model=self._model,
                    api_key=self._api_key,
                    text=text,
                    voice=self._voice,
                    language_type=self._language_type,
                    stream=True,
                )
                # Instruction control is only valid (and only billed) when we
                # actually have instructions to send.
                if self._instructions:
                    call_kwargs["instructions"] = self._instructions
                    call_kwargs["optimize_instructions"] = True

                for chunk in dashscope.MultiModalConversation.call(**call_kwargs):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:  # surface to the async side
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

        await self.start_tts_usage_metrics(text)
        producer = loop.run_in_executor(None, _produce)

        try:
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break
                if isinstance(item, Exception):
                    raise item

                audio_b64 = _deep_get(item, "output", "audio", "data")
                if not audio_b64:
                    # Final/keepalive chunks may carry no audio (e.g. usage info).
                    continue

                # First audio chunk arrived: stop the time-to-first-byte timer.
                await self.stop_ttfb_metrics()

                pcm = base64.b64decode(audio_b64)
                yield TTSAudioRawFrame(
                    audio=pcm,
                    sample_rate=self.sample_rate,
                    num_channels=1,
                    context_id=context_id,
                )
        except Exception as e:
            logger.error(f"{self}: Qwen TTS error: {e}")
            yield ErrorFrame(error=f"Qwen TTS error: {e}")
        finally:
            await self.stop_ttfb_metrics()
            # Make sure the worker thread has fully unwound before returning.
            await producer
