"""Streaming frame processor that routes LLM [emotion] tags into TTS voice changes.

Sits between the LLM and the TTS. As LLM text streams in, the processor scans
for [emotion] tags incrementally. Each time a NEW tag is found, the text
between the previous tag and the new one is a complete segment — it is
immediately emitted downstream (preceded by a TTSInstructionUpdateFrame
carrying the matching voice prompt) so TTS can start synthesizing it while the
LLM is still generating later sentences.

After the emotion tag is consumed, subsequent text is emitted sentence-by-
sentence (at . ! ? boundaries) rather than held until LLMFullResponseEndFrame.
This lets TTS start on sentence 1 while the LLM is still generating sentence 2.

At LLMFullResponseEndFrame, any text after the last sentence boundary is
flushed. If the LLM never emitted a tag, the default emotion is used.
"""

import re
from typing import Optional

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from llm_voice.frames.tts_instruction_update_frames import TTSInstructionUpdateFrame

_TAG_PATTERN = re.compile(r"\[([a-zA-Z]+)\]")
_SENTENCE_END_RE = re.compile(r'[.!?…]["\']?(?=\s|$)')


class EmotionTagProcessor(FrameProcessor):
    def __init__(
        self,
        emotion_instructions: dict[str, str],
        default_emotion: str = "calm",
    ):
        super().__init__()
        if default_emotion not in emotion_instructions:
            raise ValueError(
                f"default_emotion {default_emotion!r} not in emotion_instructions"
            )
        self._instructions = emotion_instructions
        self._default = default_emotion
        self._buffer = ""
        self._current_emotion: Optional[str] = None
        self._tag_seen = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._buffer = ""
            self._current_emotion = None
            self._tag_seen = False
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMTextFrame):
            self._buffer += frame.text
            await self._drain_complete_segments(direction)
            return

        if isinstance(frame, LLMFullResponseEndFrame):
            await self._flush_remaining(direction)
            await self.push_frame(frame, direction)
            return

        await self.push_frame(frame, direction)

    async def _drain_complete_segments(self, direction: FrameDirection):
        while True:
            match = _TAG_PATTERN.search(self._buffer)
            if not match:
                # No more tags — if we've already seen a tag, drain complete sentences now
                # so TTS starts on sentence 1 while LLM generates sentence 2.
                if self._tag_seen:
                    await self._drain_sentences(direction)
                return

            text_before = self._buffer[: match.start()].strip()
            new_emotion = match.group(1).lower()
            if new_emotion not in self._instructions:
                logger.warning(
                    f"EmotionTagProcessor: unknown emotion {new_emotion!r}, "
                    f"falling back to {self._default!r}"
                )
                new_emotion = self._default

            # Emit any text that appeared before this tag (under the previous emotion).
            if text_before:
                emotion = self._current_emotion or self._default
                await self._emit_segment(emotion, text_before, direction)

            # Immediately emit the instruction for the new emotion so TTS can
            # update before the first sentence of this segment arrives.
            self._current_emotion = new_emotion
            self._tag_seen = True
            logger.debug(f"EmotionTagProcessor: tag [{new_emotion}] → instruction update sent")
            await self.push_frame(
                TTSInstructionUpdateFrame(instructions=self._instructions[new_emotion]),
                direction,
            )
            self._buffer = self._buffer[match.end():]

    async def _drain_sentences(self, direction: FrameDirection):
        """Emit complete sentences (ending in . ! ? …) from the buffer immediately."""
        while True:
            m = _SENTENCE_END_RE.search(self._buffer)
            if not m:
                break
            sentence = self._buffer[: m.end()].strip()
            self._buffer = self._buffer[m.end() :].lstrip()
            if sentence:
                logger.debug(f"EmotionTagProcessor: emitting sentence {sentence!r}")
                await self.push_frame(LLMTextFrame(text=sentence), direction)

    async def _flush_remaining(self, direction: FrameDirection):
        leftover = self._buffer.strip()
        if not leftover:
            return
        if self._tag_seen:
            # Instruction was already sent at tag time — just emit the leftover text.
            logger.debug(f"EmotionTagProcessor: flushing remainder {leftover!r}")
            await self.push_frame(LLMTextFrame(text=leftover), direction)
        else:
            # No tag seen in this response (edge case) — use default emotion.
            emotion = self._current_emotion or self._default
            await self._emit_segment(emotion, leftover, direction)
        self._buffer = ""

    async def _emit_segment(self, emotion: str, text: str, direction: FrameDirection):
        """Emit an instruction update + text frame for a completed segment."""
        if emotion not in self._instructions:
            emotion = self._default
        logger.debug(f"EmotionTagProcessor: emitting [{emotion}] {text!r}")
        await self.push_frame(
            TTSInstructionUpdateFrame(instructions=self._instructions[emotion]),
            direction,
        )
        await self.push_frame(LLMTextFrame(text=text), direction)
