from datetime import datetime
from pathlib import Path

from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


MEMORY_FILE = (
    Path(__file__).resolve().parent.parent.parent / "memory" / "facts.md"
)
MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)


schema = FunctionSchema(
    name="remember",
    description=(
        "Save an important fact about the user to long-term memory so it can be "
        "recalled in future conversations. Call this whenever the user shares a "
        "preference, personal detail, routine, name, or explicitly asks you to "
        "remember something. Keep the fact short and self-contained."
    ),
    properties={
        "fact": {
            "type": "string",
            "description": "The fact to remember, phrased as a complete sentence.",
        },
        "tag": {
            "type": "string",
            "description": (
                "Short category label, e.g. 'preference', 'family', 'routine', "
                "'work', 'health'."
            ),
            "default": "general",
        },
    },
    required=["fact"],
)


async def handler(params: FunctionCallParams):
    fact = (params.arguments.get("fact") or "").strip()
    tag = (params.arguments.get("tag") or "general").strip()
    if not fact:
        await params.result_callback({"error": "empty fact"})
        return
    try:
        line = f"{datetime.now():%Y-%m-%d %H:%M} [{tag}] {fact}\n"
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        logger.info(f"remembered: [{tag}] {fact}")
        await params.result_callback({"saved": True, "fact": fact, "tag": tag})
    except Exception as e:
        logger.error(f"remember failed: {e}")
        await params.result_callback({"error": str(e)})
