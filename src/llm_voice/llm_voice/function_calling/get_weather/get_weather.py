import aiohttp
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


schema = FunctionSchema(
    name="get_weather",
    description=(
        "Get the current weather for a city. Use whenever the user asks about "
        "weather, temperature, rain, or conditions outside."
    ),
    properties={
        "city": {"type": "string", "description": "City name, e.g. Shanghai"},
    },
    required=["city"],
)


async def handler(params: FunctionCallParams):
    city = params.arguments.get("city", "")
    url = f"https://wttr.in/{city}?format=j1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json(content_type=None)
                current = data["current_condition"][0]
                await params.result_callback({
                    "city": city,
                    "temp_c": current["temp_C"],
                    "description": current["weatherDesc"][0]["value"],
                    "humidity": current["humidity"],
                })
    except Exception as e:
        logger.error(f"Weather lookup failed: {e}")
        await params.result_callback({"error": str(e)})
