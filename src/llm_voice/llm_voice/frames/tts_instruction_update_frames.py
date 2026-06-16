"""Shared frame types for talking to TTS services in-pipeline."""

from dataclasses import dataclass

from pipecat.frames.frames import ControlFrame


@dataclass
class TTSInstructionUpdateFrame(ControlFrame):
    """Carry a new natural-language voice prompt to the TTS.

    Processed in order with text frames so the TTS always synthesizes each
    segment with the matching instructions. Consumed by the TTS service; not
    forwarded further downstream.
    """

    instructions: str = ""
