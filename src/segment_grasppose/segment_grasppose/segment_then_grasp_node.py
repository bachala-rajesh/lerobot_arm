#!/usr/bin/env python3
"""Chain client: segment a label with SAM2, then trigger grasp detection.

Steps:
  1. call /segment_object (SAM2) with the label
  2. only if that succeeds, call /find_grasp_pose (AnyGrasp)

  ros2 run segment_grasppose segment_then_grasp <label>
  e.g.  ros2 run segment_grasppose segment_then_grasp cup

Note: the grasp service does NOT use the mask yet — it grasps the whole cleaned
cloud. This script only sequences the two calls; wiring the mask into the grasp
is a later step.
"""

from __future__ import annotations

import sys

import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_srvs.srv import Trigger

from project_interfaces.srv import SegmentObject

SEGMENT_SERVICE = "/segment_object"
GRASP_SERVICE = "/find_grasp_pose"


def call_segment(node: Node, label: str) -> SegmentObject.Response | None:
    """Ask SAM2 to segment `label`. bbox left empty -> node looks it up in scene_db."""
    client = node.create_client(SegmentObject, SEGMENT_SERVICE)
    if not client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error(
            f"{SEGMENT_SERVICE} not available. Is sam2_service running?"
        )
        return None
    req = SegmentObject.Request()
    req.label = label
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=30.0)
    if not future.done():
        node.get_logger().error("segment call timed out (30 s)")
        return None
    return future.result()


def call_grasp(node: Node) -> Trigger.Response | None:
    """Trigger the grasp server. No timeout: it blocks on the Open3D window."""
    client = node.create_client(Trigger, GRASP_SERVICE)
    if not client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error(
            f"{GRASP_SERVICE} not available. Is grasppose_server running?"
        )
        return None
    future = client.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future)  # window is blocking -> wait
    return future.result()


def main() -> None:
    rclpy.init()
    args = remove_ros_args(sys.argv)[1:]
    if not args:
        print("usage: ros2 run segment_grasppose segment_then_grasp <label>")
        print('  e.g. ros2 run segment_grasppose segment_then_grasp paper cup')
        rclpy.shutdown()
        return
    label = " ".join(args)  # join words so multi-word labels need no quotes

    node = Node("segment_then_grasp")

    node.get_logger().info(f"1/2 segmenting '{label}' ...")
    seg = call_segment(node, label)
    if seg is None or not seg.success:
        reason = seg.message if seg is not None else "no response"
        node.get_logger().error(f"segment failed: {reason}")
        node.destroy_node()
        rclpy.shutdown()
        return
    node.get_logger().info(f"segment OK: {seg.message} (score={seg.score:.3f})")

    node.get_logger().info("2/2 calling grasp service (a window will open) ...")
    grasp = call_grasp(node)
    if grasp is None:
        node.get_logger().error("grasp: no response")
    elif grasp.success:
        node.get_logger().info(f"grasp OK: {grasp.message}")
    else:
        node.get_logger().warn(f"grasp failed: {grasp.message}")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
