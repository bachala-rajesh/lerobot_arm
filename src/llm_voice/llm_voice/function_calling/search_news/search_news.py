import xml.etree.ElementTree as ET

import aiohttp
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


# China Daily English RSS — hosted in China, reachable without VPN.
FEEDS = {
    "world": "http://www.chinadaily.com.cn/rss/world_rss.xml",
    "china": "http://www.chinadaily.com.cn/rss/china_rss.xml",
    "business": "http://www.chinadaily.com.cn/rss/bizchina_rss.xml",
    "tech": "http://www.chinadaily.com.cn/rss/tech_rss.xml",
}


schema = FunctionSchema(
    name="search_news",
    description=(
        "Search for recent news headlines on a given topic. "
        "Use this when the user asks about news, recent events, or anything "
        "that requires real-time information."
    ),
    properties={
        "topic": {
            "type": "string",
            "description": "Topic keyword to filter headlines, e.g. 'AI', 'economy'",
        },
        "category": {
            "type": "string",
            "description": "News category to search within",
            "enum": list(FEEDS.keys()),
            "default": "world",
        },
    },
    required=["topic"],
)


async def _fetch_feed(session: aiohttp.ClientSession, url: str) -> list[dict]:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        text = await resp.text()
    root = ET.fromstring(text)
    items = []
    for item in root.iter("item"):
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "description": (item.findtext("description") or "").strip(),
        })
    return items


async def handler(params: FunctionCallParams):
    topic = params.arguments.get("topic", "").lower()
    category = params.arguments.get("category", "world")
    url = FEEDS.get(category, FEEDS["world"])
    try:
        async with aiohttp.ClientSession() as session:
            items = await _fetch_feed(session, url)
        if topic:
            matched = [
                i for i in items
                if topic in i["title"].lower() or topic in i["description"].lower()
            ]
            results = matched[:3] if matched else items[:3]
        else:
            results = items[:3]
        await params.result_callback({"news": results, "category": category})
    except Exception as e:
        logger.error(f"News search failed: {e}")
        await params.result_callback({"error": str(e)})
