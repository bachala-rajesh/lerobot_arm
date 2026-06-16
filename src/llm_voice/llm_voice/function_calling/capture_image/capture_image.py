import asyncio
from datetime import datetime
from pathlib import Path

import cv2
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


CAMERA_INDEX = 0           # /dev/video0
SAVE_DIR = Path("/tmp/pipcat_photos")
SAVE_DIR.mkdir(parents=True, exist_ok=True)


schema = FunctionSchema(
    name="capture_image",
    description=(
        "Capture a still image from the robot's camera and save it to disk. "
        "Use when the user asks to take a photo, look at something, or check "
        "what is currently in view. Returns the saved file path; pair with "
        "the describe_image tool if the user wants you to describe what you see."
    ),
    properties={
        "subject": {
            "type": "string",
            "description": "Short label of what is being captured, e.g. 'table', 'room'",
        },
    },
    required=["subject"],
)


def _capture_blocking(camera_index: int) -> "cv2.Mat | None":
    cap = cv2.VideoCapture(camera_index)
    try:
        ok, frame = cap.read()
        return frame if ok else None
    finally:
        cap.release()


async def handler(params: FunctionCallParams):
    subject = params.arguments.get("subject", "scene")
    try:
        frame = await asyncio.to_thread(_capture_blocking, CAMERA_INDEX)
        if frame is None:
            await params.result_callback({"error": "camera not available"})
            return

        filename = f"{subject}_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        path = SAVE_DIR / filename
        cv2.imwrite(str(path), frame)
        await params.result_callback({"saved_to": str(path), "subject": subject})
    except Exception as e:
        logger.error(f"capture_image failed: {e}")
        await params.result_callback({"error": str(e)})
