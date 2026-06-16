import base64
import os
from pathlib import Path

from loguru import logger
from openai import AsyncOpenAI

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


VL_MODEL = "qwen-vl-plus"
VL_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

_vl_client = AsyncOpenAI(
    api_key=os.getenv("PIPECAT_ALIYUN_API_KEY"),
    base_url=VL_BASE_URL,
)


schema = FunctionSchema(
    name="describe_image",
    description=(
        "Describe in natural language what is visible in an image file on disk. "
        "Use after capture_image when the user asks what you see, or to describe "
        "any saved image by path. The prompt argument lets you ask a specific "
        "question about the image (e.g. 'what color is the cup')."
    ),
    properties={
        "path": {
            "type": "string",
            "description": "Absolute path to the image file (e.g. /tmp/pipcat_photos/table_...jpg)",
        },
        "prompt": {
            "type": "string",
            "description": "What to ask about the image",
            "default": "Briefly describe what you see, one sentence.",
        },
    },
    required=["path"],
)


async def handler(params: FunctionCallParams):
    path = params.arguments.get("path", "")
    prompt = params.arguments.get(
        "prompt", "Briefly describe what you see, one sentence."
    )
    try:
        file_path = Path(path)
        if not file_path.is_file():
            await params.result_callback({"error": f"file not found: {path}"})
            return

        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        resp = await _vl_client.chat.completions.create(
            model=VL_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }],
        )
        description = resp.choices[0].message.content
        await params.result_callback({"description": description, "path": path})
    except Exception as e:
        logger.error(f"describe_image failed: {e}")
        await params.result_callback({"error": str(e)})
