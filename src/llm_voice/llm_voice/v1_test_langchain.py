#!/usr/bin/env python3
"""Phase 4.2 — Real /vlm/detect_objects wrapped as LangGraph tool.

Run from ROS2 workspace with real service running:
  source install/setup.bash
  python phase4_2_detect_objects_tool.py

Or run with FAKE=True to test without robot.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Annotated
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Set True to run without real robot/ROS2
FAKE = False


# ---------------------------------------------------------------------------
# ROS2 BRIDGE
# ---------------------------------------------------------------------------
class RosBridge:
    def __init__(self) -> None:
        import rclpy
        from rclpy.node import Node
        from so101_interfaces.srv import DetectObjects  # ← real service type

        rclpy.init()
        self.node = Node("langgraph_bridge")
        self._executor = rclpy.executors.SingleThreadedExecutor()
        self._executor.add_node(self.node)

        # TODO: create client for /vlm/detect_objects
        self._detect_client = self.node.create_client(
            DetectObjects,  # service type: DetectObjects
            "/vlm/detect_objects",  # service name: "/vlm/detect_objects"
        )

        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        self.node.get_logger().info("RosBridge started.")

    def _spin(self) -> None:
        self._executor.spin()

    def call_detect_objects(self, prompt: str) -> str:
        """Call /vlm/detect_objects. Returns formatted string for LLM."""
        import rclpy
        from so101_interfaces.srv import DetectObjects

        # TODO: build request
        req = DetectObjects.Request()
        req.prompt = prompt  # set the prompt field

        # Wait for service to be available (max 3 sec)
        if not self._detect_client.wait_for_service(timeout_sec=3.0):
            return "ERROR: /vlm/detect_objects service not available."

        # Send request and wait for response
        future = self._detect_client.call_async(req)
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=10.0)

        if future.result() is None:
            return "ERROR: service call timed out."

        res = future.result()

        # check success field
        if not res.success:  # res.success
            return "ERROR: VLM call failed."

        # TODO: format output string for LLM
        return res.description

    def shutdown(self) -> None:
        import rclpy

        self._executor.shutdown()
        self.node.destroy_node()
        rclpy.shutdown()


# ---------------------------------------------------------------------------
# FAKE BRIDGE — used when FAKE=True
# ---------------------------------------------------------------------------
class FakeRosBridge:
    def call_detect_objects(self, prompt: str) -> str:
        time.sleep(0.3)
        return (
            f"Detected: cup, bottle, pen. "
            f"Scene: There are three objects on the table — a cup on the left, "
            f"a bottle in the center, and a pen on the right."
        )

    def call_play_emotion(self, emotion: str) -> str:
        time.sleep(0.3)
        return f"Played emotion: {emotion}"

    def shutdown(self) -> None:
        pass


# ---------------------------------------------------------------------------
# GLOBAL BRIDGE
# ---------------------------------------------------------------------------
bridge: RosBridge | FakeRosBridge | None = None


def init_bridge() -> None:
    global bridge
    if FAKE:
        bridge = FakeRosBridge()
    else:
        bridge = RosBridge()


# ---------------------------------------------------------------------------
# TOOLS
# ---------------------------------------------------------------------------
@tool
def detect_objects(prompt: str) -> str:
    """Detect objects visible to the SO-101 robot camera.

    Args:
        prompt: Description of what to look for, e.g. 'objects on the table'.
    """
    return bridge.call_detect_objects(prompt)


tools = [detect_objects]
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
    system = SystemMessage(content="You control robot SO-101. Use tools when needed.")
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
    init_bridge()

    print("--- streaming tokens as they arrive ---")
    for chunk, metadata in app.stream(
        {"messages": [HumanMessage(content="What objects do you see on the table?")]},
        stream_mode="messages",  # yields (message_chunk, metadata) per token
    ):
        # metadata["langgraph_node"] tells you which node produced this chunk
        node_name = metadata.get("langgraph_node", "")

        if chunk.content:
            # tool node output — print once with label
            if node_name == "tools":
                print(f"\n[tools] {chunk.content}")
            # agent node — print tokens as they arrive
            elif node_name == "agent":
                print(chunk.content, end="", flush=True)

    print()  # newline after stream ends

    bridge.shutdown()