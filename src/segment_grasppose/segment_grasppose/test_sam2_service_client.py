#!/usr/bin/env python3
"""Test client for the /segment_object service (sam2_service node).

Query by object label (looks the bbox up in scene_db) or pass a bbox directly.
Prints the result and always shows a window with the mask overlaid on the frame.

Usage:
  ros2 run segment_grasppose test_service_client --label book
  ros2 run segment_grasppose test_service_client --bbox 100 100 300 300
  ros2 run segment_grasppose test_service_client --label cup \
      --image-topic /oak/rgb/image_raw/compressed
"""

from __future__ import annotations

import argparse
import sys

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from rclpy.utilities import remove_ros_args

from project_interfaces.srv import SegmentObject

SERVICE = "/segment_object"


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test the SAM2 segment_object service.")
    p.add_argument("--label", default="book", help="object to segment (scene_db lookup)")
    p.add_argument(
        "--bbox", type=int, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
        help="bbox to use directly; skips scene_db lookup",
    )
    p.add_argument("--image-topic", default="/oak/rgb/image_raw/compressed")
    p.add_argument("--timeout", type=float, default=30.0, help="service call timeout (s)")
    return p.parse_args(argv)


def grab_frame(node: Node, topic: str, timeout_s: float = 5.0) -> np.ndarray | None:
    """Spin briefly to catch one camera frame, decoded to RGB.

    ponytail: this is a different frame from the one the service used, so if the
    camera moved between the two the mask can look slightly off. Fine for a static
    test scene; pass --bbox on a still image if you need exact alignment.
    """
    latest: dict[str, CompressedImage] = {}
    sub = node.create_subscription(
        CompressedImage, topic, lambda m: latest.__setitem__("msg", m), 10
    )
    end = node.get_clock().now().nanoseconds + int(timeout_s * 1e9)
    while "msg" not in latest and node.get_clock().now().nanoseconds < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_subscription(sub)
    if "msg" not in latest:
        return None
    arr = np.frombuffer(latest["msg"].data, np.uint8)
    return cv2.cvtColor(cv2.imdecode(arr, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def show(rgb: np.ndarray, res: SegmentObject.Response, label: str) -> None:
    mask = np.array(res.mask_flat, np.uint8).reshape(res.mask_height, res.mask_width)
    # match mask to frame size if they differ (different camera resolution)
    if mask.shape != rgb.shape[:2]:
        mask = cv2.resize(mask, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
    m = mask.astype(bool)

    overlay = rgb.copy()
    overlay[m] = (0.5 * overlay[m] + 0.5 * np.array([0, 255, 0])).astype(np.uint8)
    cu, cv_ = int(res.centroid_u), int(res.centroid_v)
    if cu >= 0:
        cv2.circle(overlay, (cu, cv_), 5, (0, 0, 255), -1)
    cv2.putText(
        overlay, f"{label}  score={res.score:.2f}", (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
    )
    cv2.imshow("SAM2 service result", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    print("press any key on the window to close")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main() -> None:
    rclpy.init()
    args = parse_args(remove_ros_args(sys.argv)[1:])
    node = Node("sam2_service_test_client")

    client = node.create_client(SegmentObject, SERVICE)
    print(f"waiting for {SERVICE} ...")
    if not client.wait_for_service(timeout_sec=5.0):
        print(f"ERROR: {SERVICE} not available. Is sam2_service running?")
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    frame = grab_frame(node, args.image_topic)
    if frame is None:
        print(f"ERROR: no frame on {args.image_topic}. Is the camera publishing?")
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    req = SegmentObject.Request()
    req.label = args.label
    req.bbox_xyxy = list(args.bbox) if args.bbox else []

    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=args.timeout)
    if not future.done():
        print(f"ERROR: service call timed out ({args.timeout} s)")
        node.destroy_node()
        rclpy.shutdown()
        return

    res: SegmentObject.Response = future.result()
    print(f"  success  : {res.success}")
    print(f"  message  : {res.message}")
    print(f"  mask     : {res.mask_width} x {res.mask_height}")
    print(f"  centroid : ({res.centroid_u:.1f}, {res.centroid_v:.1f})")
    print(f"  score    : {res.score:.3f}")

    if res.success:
        show(frame, res, args.label)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
