#!/usr/bin/env python3

"""v5 — v4 + real scene_db tools (instead of fake).

What's new vs v4:
    1. Real @tool functions reading from scene_db (SQLite).
    2. Blocking SceneDB calls wrapped with asyncio.to_thread inside tool_node
       — so the audio loop never freezes.

scene_db is a PURE PYTHON library — no rclpy, no event loop dance.
Just import it like any Python module.

Run:
    # 1. Source the workspace so scene_db can be imported
    source ~/workspaces/lerobot_ws/install/setup.bash

    # 2. Set Qwen API key
    export PIPECAT_ALIYUN_API_KEY=...

    # 3. Run
    python v5_scene_db_tools.py

Try saying:
    "What objects have you seen recently?"
    "Have you seen a smartwatch?"
    "Tell me about the cups in the scene."
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/home/mira/code/pipcat_robot")

import asyncio
import os
import sys
import time
from typing import Annotated, AsyncIterator
from typing_extensions import TypedDict

import dashscope

# Pipecat
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frameworks.langchain import LangchainProcessor
from pipecat.transports.local.audio import (
    LocalAudioTransport,
    LocalAudioTransportParams,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer

# LangChain / LangGraph
from langchain_core.messages import (
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Local services (same as l7 / v1 / v4)
from llm_voice.services.stt.stt_qwen3_flash import Qwen3FlashSTTService
from llm_voice.services.tts.tts_qwen3_flash import QwenTTSService

# ---------------------------------------------------------------------------
# scene_db import — pure Python, no ROS event loop
# Works after: source ~/workspaces/lerobot_ws/install/setup.bash
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.expanduser("~/workspaces/lerobot_ws/src/scene_db"))
from scene_db.database import SceneDB, Detection


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
QWEN_API_KEY = os.getenv("PIPECAT_ALIYUN_API_KEY")
QWEN_VOICE = "Mochi"


# ===========================================================================
# PART 1 — scene_db setup
# ===========================================================================
# Open the DB once. Tools share this single instance.
# ---------------------------------------------------------------------------

db = SceneDB()
print(f"[v5] scene_db opened at: {db.path}")
total, pending = db.count()
print(f"[v5] DB rows: {total} total, {pending} pending 3D")


def detection_to_str(d: Detection) -> str:
    """Format a single Detection row into a short, speakable string."""
    age_sec = int(time.time() - d.detected_at)
    if d.world_xyz:
        x, y, z = d.world_xyz
        return f"{d.label} seen {age_sec}s ago at ({x:.2f}, {y:.2f}, {z:.2f})"
    return f"{d.label} seen {age_sec}s ago, no 3D position yet"


# ===========================================================================
# PART 2 — TOOLS (real scene_db queries)
# ===========================================================================


@tool
def query_recent_scene(limit: int = 5) -> str:
    """List the most recent object detections from the robot's scene database.

    Use when the user asks what objects are present, what the robot has seen,
    or anything about the current scene.

    Args:
        limit: Maximum number of recent detections to return (default 5).
    """
    detections = db.query_recent(limit=limit)
    if not detections:
        return "I have not detected any objects yet."
    lines = [detection_to_str(d) for d in detections]
    return "Recent objects: " + "; ".join(lines)


@tool
def query_scene_by_label(label: str, max_age_sec: float = 60.0) -> str:
    """Search the scene database for a specific object by name.

    Use when the user asks about a specific object, e.g. "have you seen a cup?".

    Args:
        label: Object name, e.g. 'cup', 'bottle', 'smartwatch'.
        max_age_sec: Only return detections within this many seconds (default 60).
    """
    detections = db.query_by_label(label=label, max_age_sec=max_age_sec, limit=3)
    if not detections:
        return f"I have not seen any {label} in the last {int(max_age_sec)} seconds."
    lines = [detection_to_str(d) for d in detections]
    return f"Found {len(detections)} {label}: " + "; ".join(lines)


tools = [query_recent_scene, query_scene_by_label]
tools_by_name = {t.name: t for t in tools}


# ===========================================================================
# PART 3 — LANGGRAPH
# ===========================================================================

llm = ChatOpenAI(
    model="qwen-plus",
    api_key=QWEN_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
llm_with_tools = llm.bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list, add_messages]


async def agent_node(state: State) -> dict:
    system = SystemMessage(
        content=(
            "You are a friendly robot connected to a vision system that logs "
            "object detections. Use tools to answer questions about what "
            "you've seen. After getting tool results, reply in ONE short "
            "sentence. Your reply will be spoken aloud — no markdown, "
            "no emojis, no special characters."
        )
    )
    response = await llm_with_tools.ainvoke([system] + state["messages"])
    return {"messages": [response]}


async def tool_node(state: State) -> dict:
    """Run requested tools. Blocking calls are pushed to a worker thread
    so the audio event loop stays free."""
    last_message = state["messages"][-1]
    results = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        # SceneDB.query_* is sync SQLite. Wrap with asyncio.to_thread
        # so the audio loop is not blocked while SQLite runs.
        output = await asyncio.to_thread(tool_fn.invoke, tool_call["args"])
        results.append(
            ToolMessage(content=str(output), tool_call_id=tool_call["id"])
        )
    return {"messages": results}


def should_continue(state: State) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


graph_builder = StateGraph(State)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", should_continue)
graph_builder.add_edge("tools", "agent")
app = graph_builder.compile()


# ===========================================================================
# PART 4 — ADAPTER (unchanged from v1 / v4)
# ===========================================================================


async def langgraph_adapter(inputs: dict) -> AsyncIterator[AIMessageChunk]:
    user_text: str = inputs["input"]
    state = {"messages": [HumanMessage(content=user_text)]}

    async for chunk, metadata in app.astream(state, stream_mode="messages"):
        if isinstance(chunk, AIMessageChunk) and chunk.content.strip():
            yield chunk


adapter = RunnableLambda(langgraph_adapter)


# ===========================================================================
# PART 5 — PIPELINE (unchanged from v1 / v4)
# ===========================================================================


async def main():
    transport = LocalAudioTransport(
        params=LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_in_sample_rate=16000,
            audio_in_channels=1,
            audio_out_enabled=True,
            audio_out_sample_rate=24000,
            audio_out_channels=1,
        )
    )

    stt = Qwen3FlashSTTService(
        api_key=QWEN_API_KEY,
        model="qwen3-asr-flash",
        language_hints="en",
        sample_rate=16000,
        stream=True,
    )

    brain = LangchainProcessor(adapter)

    tts = QwenTTSService(
        api_key=QWEN_API_KEY,
        voice=QWEN_VOICE,
        model="qwen3-tts-flash",
        language_type=("en"),
        sample_rate=24000,
    )

    messages = [{"role": "user", "content": "Start by introducing yourself."}]
    context = LLMContext(messages)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            brain,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    runner = PipelineRunner()
    task = PipelineTask(pipeline)
    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
