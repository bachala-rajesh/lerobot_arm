#!/usr/bin/env python3
"""Tiny client: call /find_grasp_pose (Trigger) once, print the reply.

The server grabs the latest OAK-D cloud, runs AnyGrasp, and opens an Open3D
window. It only replies after you CLOSE that window — so this client waits
(no timeout) until the window is closed.

  ros2 run segment_grasppose grasppose_client
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

SERVICE = "/find_grasp_pose"


def main() -> None:
    rclpy.init()
    node = Node("grasppose_client")

    client = node.create_client(Trigger, SERVICE)
    node.get_logger().info(f"waiting for {SERVICE} ...")
    if not client.wait_for_service(timeout_sec=10.0):
        node.get_logger().error(f"{SERVICE} not available. Is grasppose_server running?")
        node.destroy_node()
        rclpy.shutdown()
        return

    node.get_logger().info("calling — a window will open; close it to get the reply")
    future = client.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future)  # no timeout: window is blocking

    result = future.result()
    if result.success:
        node.get_logger().info(f"OK: {result.message}")
    else:
        node.get_logger().warn(f"failed: {result.message}")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
