#!/usr/bin/env python3
"""Phase 4.3 — scene_db queries wrapped as LangGraph tools.

SceneDB is a pure Python lib — no ROS bridge needed.
Import it directly. Must run with lerobot_ws sourced:
  source ~/workspaces/lerobot_ws/install/setup.bash
  python phase4_3_scene_db_tools.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Annotated
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# ---------------------------------------------------------------------------
# scene_db import — works after: source install/setup.bash
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.expanduser("~/workspaces/lerobot_ws/src/scene_db"))
from scene_db.database import SceneDB, Detection


# ---------------------------------------------------------------------------
# HELPER — format one Detection into a string the LLM can read
# ---------------------------------------------------------------------------
def detection_to_str(d: Detection) -> str:
    age_sec = int(time.time() - d.detected_at)

    # TODO: build a string with: label, age, world_xyz (if available)
    # Example: "cup — seen 5s ago, 3D pos: (0.30, 0.10, 0.05)"
    # Example (no 3D): "bottle — seen 12s ago, no 3D position yet"
    if d.world_xyz:
        x, y, z = d.world_xyz
        return f"{d.label}  seen {age_sec}s ago, 3D pos: ({x:.2f}, {y:.2f}, {z:.2f})"
    else:
        return f"{d.label} — seen {age_sec}s ago, no 3D position yet"


# ---------------------------------------------------------------------------
# GLOBAL DB — opened once, shared by all tool calls
# ---------------------------------------------------------------------------
db: SceneDB | None = None


def init_db() -> None:
    global db
    db = (
        SceneDB()
    )  # uses DEFAULT_DB_PATH from env or ~/workspaces/lerobot_ws/src/scene_db/scene.db


# ---------------------------------------------------------------------------
# TOOL 1: query_recent_scene
# ---------------------------------------------------------------------------
@tool
def query_recent_scene(limit: int = 10) -> str:
    """Query the most recent object detections from the scene database.

    Args:
        limit: Maximum number of recent detections to return (default 10).
    """
    detections = db.query_recent(limit=limit)

    if not detections:
        return "No detections in scene database."

    # TODO: format list of detections into one string
    # Use detection_to_str(d) for each detection d
    lines = [detection_to_str(d) for d in detections]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# TOOL 2: query_scene_by_label
# ---------------------------------------------------------------------------
@tool
def query_scene_by_label(label: str, max_age_sec: float = 60.0) -> str:
    """Search scene database for a specific object by label.

    Args:
        label: Object name to search for, e.g. 'cup', 'bottle'.
        max_age_sec: Only return detections within this many seconds (default 60).
    """
    detections = db.query_by_label(
        label=label,
        max_age_sec=max_age_sec,
        limit=5,
    )

    if not detections:
        return f"No '{label}' found in scene database within last {max_age_sec:.0f}s."

    # TODO: format list of detections into one string
    lines = [detection_to_str(d) for d in detections]  # same pattern as above
    return f"Found {len(detections)} '{label}':\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# GRAPH
# ---------------------------------------------------------------------------
tools = [query_recent_scene, query_scene_by_label]
tools_by_name = {t.name: t for t in tools}

llm = ChatOpenAI(
    model="qwen-max",
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
llm_with_tools = llm.bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def agent_node(state: State) -> dict:
    system = SystemMessage(
        content=(
            "You control robot SO-101. You have access to a scene database "
            "that stores past object detections. Use tools to answer questions."
        )
    )
    response = llm_with_tools.invoke([system] + state["messages"])
    return {"messages": [response]}


def tool_node(state: State) -> dict:
    last_message = state["messages"][-1]
    results = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        output = tool_fn.invoke(tool_call["args"])
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
graph_builder.add_edge("tools", "agent")
graph_builder.add_conditional_edges("agent", should_continue)
app = graph_builder.compile()

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print(f"DB path: {db.path}")
    total, pending = db.count()
    print(f"DB rows: {total} total, {pending} pending 3D")

    questions = [
        "What objects have been seen recently?",
        "Has any smartwatch seen in the last 10 minutes?",
    ]

    for q in questions:
        print(f"\n{'=' * 50}\nQ: {q}")
        for chunk, metadata in app.stream(
            {"messages": [HumanMessage(content=q)]},
            stream_mode="messages",
        ):
            node_name = metadata.get("langgraph_node", "")
            if chunk.content:
                if node_name == "tools":
                    print(f"\n[tools] {chunk.content}")
                elif node_name == "agent":
                    print(chunk.content, end="", flush=True)
    print()
