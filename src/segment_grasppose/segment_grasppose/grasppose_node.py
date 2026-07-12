#!/usr/bin/env python3
"""Grasp-pose node — step 1: SAM2 mask -> masked point cloud -> Open3D.

Pipeline (one-shot):
  1. Grab the latest organized point cloud from /oak/points.
  2. Call the /segment_object service with a label -> get the object mask.
  3. Map the mask onto the cloud grid, keep only the object's 3D points.
  4. Show those points in an Open3D window (with an origin axis).

The cloud is organized (one point per pixel) and aligned to the RGB frame, so
the mask indexes it directly — no camera intrinsics needed here.

Usage:
  ros2 run segment_grasppose grasppose_node --label book
  ros2 run segment_grasppose grasppose_node --label "pen holder"
  ros2 run segment_grasppose grasppose_node --bbox 605 355 1053 684
"""

from __future__ import annotations

import argparse
import sys

import cv2
import numpy as np
import open3d as o3d
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2

from project_interfaces.srv import SegmentObject

SERVICE = "/segment_object"


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SAM2 mask -> masked point cloud -> Open3D.")
    p.add_argument("--label", default="book", help="object to segment (scene_db lookup)")
    p.add_argument(
        "--bbox", type=int, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
        help="bbox to use directly; skips scene_db lookup",
    )
    p.add_argument("--cloud-topic", default="/oak/points")
    p.add_argument("--timeout", type=float, default=30.0, help="service call timeout (s)")
    return p.parse_args(argv)


def grab_cloud(node: Node, topic: str, timeout_s: float = 5.0) -> PointCloud2 | None:
    """Spin briefly to catch one point cloud message."""
    latest: dict[str, PointCloud2] = {}
    sub = node.create_subscription(
        PointCloud2, topic, lambda m: latest.__setitem__("msg", m), 10
    )
    end = node.get_clock().now().nanoseconds + int(timeout_s * 1e9)
    while "msg" not in latest and node.get_clock().now().nanoseconds < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_subscription(sub)
    return latest.get("msg")


def call_segment(node: Node, label: str, bbox: list[int] | None,
                 timeout_s: float) -> SegmentObject.Response | None:
    client = node.create_client(SegmentObject, SERVICE)
    print(f"waiting for {SERVICE} ...")
    if not client.wait_for_service(timeout_sec=5.0):
        print(f"ERROR: {SERVICE} not available. Is sam2_service running?")
        return None
    req = SegmentObject.Request()
    req.label = label
    req.bbox_xyxy = list(bbox) if bbox else []
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_s)
    if not future.done():
        print(f"ERROR: service call timed out ({timeout_s} s)")
        return None
    return future.result()


def masked_points(cloud: PointCloud2, res: SegmentObject.Response) -> np.ndarray:
    """Return the object's 3D points (N, 3), NaN/inf dropped."""
    # organized cloud -> (H, W, 3)
    xyz = point_cloud2.read_points_numpy(
        cloud, field_names=("x", "y", "z"), reshape_organized_cloud=True
    )
    mask = np.array(res.mask_flat, np.uint8).reshape(res.mask_height, res.mask_width)
    # match mask grid to the cloud grid (depth may differ in resolution from RGB)
    if mask.shape != xyz.shape[:2]:
        mask = cv2.resize(
            mask, (xyz.shape[1], xyz.shape[0]), interpolation=cv2.INTER_NEAREST
        )
    pts = xyz[mask.astype(bool)]
    return pts[np.isfinite(pts).all(axis=1)]


def show(pts: np.ndarray) -> None:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    # small axis at the camera origin for scale/orientation reference
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
    print("close the Open3D window to finish")
    o3d.visualization.draw_geometries([pcd, axis], window_name="grasppose: masked cloud")


def main() -> None:
    rclpy.init()
    args = parse_args(remove_ros_args(sys.argv)[1:])
    node = Node("grasppose_node")

    cloud = grab_cloud(node, args.cloud_topic)
    if cloud is None:
        print(f"ERROR: no cloud on {args.cloud_topic}. Is the point cloud publishing?")
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    res = call_segment(node, args.label, args.bbox, args.timeout)
    if res is None:
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    print(f"  success  : {res.success}")
    print(f"  message  : {res.message}")
    print(f"  score    : {res.score:.3f}")
    if not res.success:
        node.destroy_node()
        rclpy.shutdown()
        return

    pts = masked_points(cloud, res)
    print(f"  points   : {len(pts)} in the mask (after NaN drop)")
    if len(pts) == 0:
        print("no valid 3D points under the mask — is depth valid there?")
    else:
        show(pts)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
