#!/usr/bin/env python3

"""
v6 — v5 + debug prints to trace which LangGraph node emits each chunk.

Purpose: understand where "let me look right now" comes from — agent_node call 1
or agent_node call 2.

Run:
    ros2 run llm_voice v6_debug.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
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

# Local Pipecat services
from llm_voice.services.stt.stt_qwen3_flash import Qwen3FlashSTTService
from llm_voice.services.tts.tts_qwen3_flash import QwenTTSService

# scene_db (pure Python — no rclpy)
sys.path.insert(0, os.path.expanduser("~/workspaces/lerobot_ws/src/scene_db"))
from scene_db.database import SceneDB, Detection


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
QWEN_API_KEY = os.getenv("PIPECAT_ALIYUN_API_KEY")
QWEN_VOICE = "Mochi"


# ===========================================================================
# PART 1 — ROS BRIDGE
# ===========================================================================

class RosBridge:
    """ROS2 bridge: rclpy.Node + background spin thread + service client."""

    def __init__(self) -> None:
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from project_interfaces.srv import DetectObjects

        rclpy.init()
        self.node = Node("voice_agent_bridge")

        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self.node)

        self._detect_client = self.node.create_client(
            DetectObjects, "/vlm/detect_objects"
        )

        self._thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._thread.start()
        self.node.get_logger().info("RosBridge started.")

    def call_detect_objects(self, prompt: str) -> str:
        from project_interfaces.srv import DetectObjects

        if not self._detect_client.wait_for_service(timeout_sec=3.0):
            return "ERROR: /vlm/detect_objects service not available."

        req = DetectObjects.Request()
        req.prompt = prompt
        future = self._detect_client.call_async(req)

        deadline = time.time() + 10.0
        while not future.done():
            if time.time() > deadline:
                return "ERROR: detect_objects service call timed out."
            time.sleep(0.02)

        res = future.result()
        if res is None:
            return "ERROR: detect_objects returned no result."
        if not res.success:
            return "ERROR: VLM call failed."
        return res.description

    def shutdown(self) -> None:
        import rclpy
        self._executor.shutdown()
        self.node.destroy_node()
        rclpy.shutdown()


bridge: RosBridge | None = None


# ===========================================================================
# PART 2 — scene_db
# ===========================================================================

db = SceneDB()
print(f"[v6] scene_db opened at: {db.path}")
total, pending = db.count()
print(f"[v6] DB rows: {total} total, {pending} pending 3D")


def detection_to_str(d: Detection) -> str:
    age_sec = int(time.time() - d.detected_at)
    if d.world_xyz:
        x, y, z = d.world_xyz
        return f"{d.label} seen {age_sec}s ago at ({x:.2f}, {y:.2f}, {z:.2f})"
    return f"{d.label} seen {age_sec}s ago, no 3D position yet"


# ===========================================================================
# PART 3 — TOOLS
# ===========================================================================

@tool
def detect_objects(prompt: str) -> str:
    """Look at the scene RIGHT NOW with the camera and answer a visual question.

    Use when the user asks the robot to look, see, check, scan, describe,
    or compare what is currently visible. Takes about 3-4 seconds.

    Args:
        prompt: A clear, detailed question for the vision model.
    """
    return bridge.call_detect_objects(prompt)


@tool
def query_recent_scene(limit: int = 5) -> str:
    """Recall recent object detections from the scene memory database.

    Use when the user asks what you have seen recently or in the past.
    This is fast — no new camera capture.

    Args:
        limit: Max number of recent detections to return (default 5).
    """
    detections = db.query_recent(limit=limit)
    if not detections:
        return "I have not detected any objects yet."
    return "Recent objects: " + "; ".join(detection_to_str(d) for d in detections)


@tool
def query_scene_by_label(label: str, max_age_sec: float = 60.0) -> str:
    """Search scene memory for a specific object by name.

    Args:
        label: Object name, e.g. 'cup', 'bottle', 'smartwatch'.
        max_age_sec: Only return detections newer than this many seconds.
    """
    detections = db.query_by_label(label=label, max_age_sec=max_age_sec, limit=3)
    if not detections:
        return f"I have not seen any {label} in the last {int(max_age_sec)} seconds."
    return f"Found {len(detections)} {label}: " + "; ".join(
        detection_to_str(d) for d in detections
    )


tools = [detect_objects, query_recent_scene, query_scene_by_label]
tools_by_name = {t.name: t for t in tools}


# ===========================================================================
# PART 4 — LANGGRAPH
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
    # ── DEBUG: show full message history on every agent_node call ──
    print(f"\n[AGENT_NODE] called — {len(state['messages'])} messages in state:")
    for i, m in enumerate(state["messages"]):
        content_preview = repr(str(m.content)[:120])
        tool_calls = getattr(m, "tool_calls", [])
        tool_names = [tc["name"] for tc in tool_calls] if tool_calls else []
        print(f"  [{i}] {type(m).__name__}: content={content_preview} tool_calls={tool_names}")
    print()

    system = SystemMessage(
        content=(
            "You are a friendly robot with a camera and a scene memory database. "
            "Use detect_objects to LOOK with the camera right now. "
            "Use query_recent_scene or query_scene_by_label to recall past detections. "
            "After tool results, reply in ONE short sentence. "
            "Your reply will be spoken aloud — no markdown, no emojis, "
            "no special characters."
        )
    )
    full = None
    async for piece in llm_with_tools.astream([system] + state["messages"]):
        full = piece if full is None else full + piece

    # ── DEBUG: show what agent_node is returning ──
    print(f"[AGENT_NODE] returning — content={repr(str(full.content)[:120])} tool_calls={[tc['name'] for tc in getattr(full, 'tool_calls', [])]}")

    return {"messages": [full]}


async def tool_node(state: State) -> dict:
    last_message = state["messages"][-1]
    results = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        output = await asyncio.to_thread(tool_fn.invoke, tool_call["args"])
        print(f"\n[TOOL_NODE] {tool_call['name']} returned: {repr(str(output)[:120])}")
        results.append(ToolMessage(content=str(output), tool_call_id=tool_call["id"]))
    return {"messages": results}


def should_continue(state: State) -> str:
    if state["messages"][-1].tool_calls:
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
# PART 5 — ADAPTER
# ===========================================================================

async def langgraph_adapter(inputs: dict) -> AsyncIterator[AIMessageChunk]:
    user_text: str = inputs["input"]
    state = {"messages": [HumanMessage(content=user_text)]}

    print(f"\n[ADAPTER] starting stream for input: {repr(user_text)}")

    async for chunk, metadata in app.astream(state, stream_mode="messages"):
        node = metadata.get("langgraph_node", "?")
        chunk_type = type(chunk).__name__
        content = chunk.content if hasattr(chunk, "content") else ""
        tool_call_chunks = getattr(chunk, "tool_call_chunks", [])
        tool_names = [tc.get("name", "") for tc in tool_call_chunks if tc.get("name")]

        # ── DEBUG: every chunk from every node ──
        print(
            f"[ADAPTER] node={node:10s} type={chunk_type:20s} "
            f"content={repr(content[:60]):30s} tool_call_chunks={tool_names}"
        )

        if isinstance(chunk, AIMessageChunk) and chunk.content.strip():
            if chunk.tool_call_chunks:
                pass  # Qwen added text alongside tool call — drop it
            else:
                yield chunk


adapter = RunnableLambda(langgraph_adapter)


# ===========================================================================
# PART 6 — PIPELINE
# ===========================================================================

async def main():
    global bridge
    bridge = RosBridge()

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
    try:
        await runner.run(task)
    finally:
        bridge.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
