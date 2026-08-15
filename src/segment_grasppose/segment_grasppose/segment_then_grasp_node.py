#!/usr/bin/env python3
"""Chain client: segment a label with SAM2, mask the cloud, run AnyGrasp.

Steps:
  1. call /segment_object (SAM2) with the label            -> 2D mask
  2. grab one /oak/points cloud, apply the mask            -> object-only cloud
  3. call /find_grasp_pose (GraspFromCloud) with that cloud -> grasp + window

  ros2 run segment_grasppose segment_then_grasp paper cup

Offline check of the mask -> object-cloud step (no ROS graph needed):
  python3 segment_then_grasp_node.py --selfcheck
"""

from __future__ import annotations

import sys

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header

from project_interfaces.srv import GraspFromCloud, SegmentObject

SEGMENT_SERVICE = "/segment_object"
GRASP_SERVICE = "/find_grasp_pose"
CLOUD_TOPIC = "/oak/points"

# tightly-packed xyz + rgb; the server reads by field name, so offsets are ours.
_FIELDS = [
    PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
    PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
    PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    PointField(name="rgb", offset=12, datatype=PointField.FLOAT32, count=1),
]


def mask_to_object_cloud(
    cloud: PointCloud2, mask_flat, mask_h: int, mask_w: int
) -> tuple[PointCloud2, int]:
    """Apply the SAM2 mask to the organized cloud -> object-only PointCloud2.

    The cloud is organized (H, W) and aligned to the RGB frame; the mask comes
    from SAM2 at image resolution, so we resize it to the cloud grid. rgb is
    passed through untouched — no unpack/repack, so colours cannot drift.
    """
    arr = point_cloud2.read_points(
        cloud, field_names=("x", "y", "z", "rgb"), reshape_organized_cloud=True
    )  # structured array, shape (H, W)

    mask = np.array(mask_flat, np.uint8).reshape(mask_h, mask_w)
    if mask.shape != arr.shape:
        mask = cv2.resize(
            mask, (arr.shape[1], arr.shape[0]), interpolation=cv2.INTER_NEAREST
        )

    sel = arr[mask.astype(bool)]  # (N,) structured
    finite = np.isfinite(sel["x"]) & np.isfinite(sel["y"]) & np.isfinite(sel["z"])
    sel = sel[finite]

    pts = [(r["x"], r["y"], r["z"], r["rgb"]) for r in sel]
    return point_cloud2.create_cloud(cloud.header, _FIELDS, pts), len(pts)


def grab_cloud(node: Node, timeout_s: float = 5.0) -> PointCloud2 | None:
    """Spin briefly to catch one cloud. Best-effort QoS matches the publisher."""
    latest: dict[str, PointCloud2] = {}
    sub = node.create_subscription(
        PointCloud2,
        CLOUD_TOPIC,
        lambda m: latest.__setitem__("msg", m),
        qos_profile_sensor_data,
    )
    end = node.get_clock().now().nanoseconds + int(timeout_s * 1e9)
    while "msg" not in latest and node.get_clock().now().nanoseconds < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_subscription(sub)
    return latest.get("msg")


def call_segment(node: Node, label: str) -> SegmentObject.Response | None:
    """Ask SAM2 to segment `label`. Empty bbox -> node looks it up in scene_db."""
    client = node.create_client(SegmentObject, SEGMENT_SERVICE)
    if not client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error(
            f"{SEGMENT_SERVICE} not available. Is sam2_server running?"
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


def call_grasp(node: Node, cloud: PointCloud2) -> GraspFromCloud.Response | None:
    """Send the object cloud. No timeout: the server blocks on its window."""
    client = node.create_client(GraspFromCloud, GRASP_SERVICE)
    if not client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error(
            f"{GRASP_SERVICE} not available. Is grasppose_server running?"
        )
        return None
    req = GraspFromCloud.Request()
    req.cloud = cloud
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future)  # window is blocking -> wait
    return future.result()


def main() -> None:
    rclpy.init()
    args = remove_ros_args(sys.argv)[1:]
    if not args:
        print("usage: ros2 run segment_grasppose segment_then_grasp <label>")
        print("  e.g. ros2 run segment_grasppose segment_then_grasp paper cup")
        rclpy.shutdown()
        return
    label = " ".join(args)  # join words so multi-word labels need no quotes

    node = Node("segment_then_grasp")

    node.get_logger().info(f"1/3 segmenting '{label}' ...")
    seg = call_segment(node, label)
    if seg is None or not seg.success:
        reason = seg.message if seg is not None else "no response"
        node.get_logger().error(f"segment failed: {reason}")
        node.destroy_node()
        rclpy.shutdown()
        return
    node.get_logger().info(f"segment OK: {seg.message} (score={seg.score:.3f})")

    node.get_logger().info("2/3 grabbing cloud + applying mask ...")
    cloud = grab_cloud(node)
    if cloud is None:
        node.get_logger().error(f"no cloud on {CLOUD_TOPIC}. Is the pointcloud up?")
        node.destroy_node()
        rclpy.shutdown()
        return
    obj_cloud, n = mask_to_object_cloud(
        cloud, seg.mask_flat, seg.mask_height, seg.mask_width
    )
    node.get_logger().info(f"object cloud: {n} points")
    if n == 0:
        node.get_logger().error("mask selected 0 valid points — nothing to grasp")
        node.destroy_node()
        rclpy.shutdown()
        return

    node.get_logger().info("3/3 calling grasp service (a window will open) ...")
    grasp = call_grasp(node, obj_cloud)
    if grasp is None:
        node.get_logger().error("grasp: no response")
    elif grasp.success:
        node.get_logger().info(f"grasp OK: {grasp.message}")
    else:
        node.get_logger().warn(f"grasp failed: {grasp.message}")

    node.destroy_node()
    rclpy.shutdown()


def _pack_rgb(r: int, g: int, b: int) -> float:
    """r,g,b (0..255) -> the single float32 the cloud stores (0x00RRGGBB)."""
    packed = np.array([(r << 16) | (g << 8) | b], dtype=np.uint32)
    return float(packed.view(np.float32)[0])


def _selfcheck() -> None:
    """Build a 2x2 organized cloud (one NaN), mask 3 cells, expect 2 survive."""
    pts = [
        (0.0, 0.0, 1.0, _pack_rgb(255, 0, 0)),      # masked, finite -> keep
        (1.0, 0.0, 1.0, _pack_rgb(0, 255, 0)),      # not masked
        (float("nan"), 0.0, 1.0, _pack_rgb(0, 0, 255)),  # masked but NaN -> drop
        (0.0, 1.0, 1.0, _pack_rgb(255, 255, 0)),    # masked, finite -> keep
    ]
    cloud = point_cloud2.create_cloud(Header(frame_id="test"), _FIELDS, pts)
    cloud.height, cloud.width = 2, 2
    cloud.row_step = cloud.point_step * 2
    cloud.is_dense = False

    obj, n = mask_to_object_cloud(cloud, [1, 0, 1, 1], 2, 2)
    assert n == 2, f"expected 2 points (NaN dropped), got {n}"

    back = point_cloud2.read_points(obj, field_names=("x", "y", "z"), skip_nans=True)
    assert len(back) == 2, len(back)
    print("mask_to_object_cloud OK")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        main()
