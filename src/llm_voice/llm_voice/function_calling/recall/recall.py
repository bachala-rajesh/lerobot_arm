from pathlib import Path

from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


MEMORY_FILE = (
    Path(__file__).resolve().parent.parent.parent / "memory" / "facts.md"
)


schema = FunctionSchema(
    name="recall",
    description=(
        "Search long-term memory for facts about the user. Call this when the "
        "user asks what you remember about a topic, or when you need background "
        "information that may have been saved in a past conversation. Returns "
        "matching memory lines."
    ),
    properties={
        "query": {
            "type": "string",
            "description": (
                "Keyword to search for in memory. If empty, returns all stored "
                "facts."
            ),
            "default": "",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of matches to return.",
            "default": 10,
        },
    },
    required=[],
)


def load_all_facts() -> list[str]:
    if not MEMORY_FILE.exists():
        return []
    return [
        line.strip()
        for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


async def handler(params: FunctionCallParams):
    query = (params.arguments.get("query") or "").strip().lower()
    limit = int(params.arguments.get("limit") or 10)
    try:
        facts = load_all_facts()
        if not facts:
            await params.result_callback({"matches": [], "note": "memory is empty"})
            return
        if query:
            matches = [f for f in facts if query in f.lower()]
        else:
            matches = facts
        await params.result_callback({
            "matches": matches[-limit:],
            "total_stored": len(facts),
        })
    except Exception as e:
        logger.error(f"recall failed: {e}")
        await params.result_callback({"error": str(e)})
