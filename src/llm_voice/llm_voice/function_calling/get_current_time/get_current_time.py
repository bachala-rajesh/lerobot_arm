from datetime import datetime

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


schema = FunctionSchema(
    name="get_current_time",
    description=(
        "Get the current local date and time. Use when the user asks what time "
        "it is, what day it is, or today's date."
    ),
    properties={},
    required=[],
)


async def handler(params: FunctionCallParams):
    now = datetime.now()
    await params.result_callback({
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "weekday": now.strftime("%A"),
    })
