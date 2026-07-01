#!/usr/bin/env python3
"""
Test client for /vlm/detect_objects.


"""
from __future__ import annotations

import argparse
import sys

import rclpy
from rclpy.node import Node

from so101_interfaces.srv import DetectObjects


class VlmTestClient(Node):
    def __init__(self, service_name: str) -> None:
        super().__init__("vlm_test_client")
        self._client = self.create_client(DetectObjects, service_name)
        self._service_name = service_name

    def call(self, prompt: str, timeout_sec: float = 30.0) -> DetectObjects.Response | None:
        # Wait for the service to be up
        self.get_logger().info(f"Waiting for service {self._service_name} ...")
        if not self._client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error("Service not available after 10 s.")
            return None

        request = DetectObjects.Request()
        request.prompt = prompt

        self.get_logger().info(f"Sending prompt: '{prompt}'")
        future = self._client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)

        if not future.done():
            self.get_logger().error(f"Service call timed out after {timeout_sec} s.")
            return None
        return future.result()


def print_response(resp: DetectObjects.Response) -> None:
    print("\n===== VLM Response =====")
    print(f"success         : {resp.success}")
    print(f"image size      : {resp.image_width} x {resp.image_height}")
    print(f"stamp           : {resp.stamp.sec}.{resp.stamp.nanosec}")
    print(f"description     : {resp.description}")
    print(f"# detections    : {len(resp.labels)}")

    # Decode flat bboxes — 4 ints per detection
    bboxes = list(resp.bboxes_xyxy)
    for i, label in enumerate(resp.labels):
        x1, y1, x2, y2 = bboxes[i * 4 : i * 4 + 4]
        print(f"  [{i}] {label:20s} -> ({x1},{y1}) -> ({x2},{y2})")
    print("========================\n")


def visualise(resp: DetectObjects.Response, image_topic: str) -> None:
    """Subscribe to the live camera once, draw bboxes, show with OpenCV."""
    import cv2
    import numpy as np
    from sensor_msgs.msg import CompressedImage, Image

    node = rclpy.create_node("vlm_test_viewer")
    got_frame: dict = {"frame": None}

    is_compressed = image_topic.endswith("/compressed")

    if is_compressed:
        def cb(msg: CompressedImage) -> None:
            arr = np.frombuffer(msg.data, dtype=np.uint8)
            got_frame["frame"] = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        node.create_subscription(CompressedImage, image_topic, cb, 10)
    else:
        def cb(msg: Image) -> None:  # type: ignore[misc]
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, -1))
            if msg.encoding == "rgb8":
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            got_frame["frame"] = frame.copy()
        node.create_subscription(Image, image_topic, cb, 10)

    # Spin briefly to grab one frame
    end_time = node.get_clock().now().nanoseconds + int(3.0 * 1e9)
    while got_frame["frame"] is None and node.get_clock().now().nanoseconds < end_time:
        rclpy.spin_once(node, timeout_sec=0.1)

    if got_frame["frame"] is None:
        node.get_logger().warn(f"No frame on {image_topic} within 3 s; skipping display.")
        node.destroy_node()
        return

    frame = got_frame["frame"].copy()
    bboxes = list(resp.bboxes_xyxy)
    for i, label in enumerate(resp.labels):
        x1, y1, x2, y2 = bboxes[i * 4 : i * 4 + 4]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, max(y1 - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

    cv2.imshow("VLM detections (press any key to close)", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    node.destroy_node()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test client for /vlm/detect_objects")
    p.add_argument("--prompt", default="Find objects in the image", help="user prompt")
    p.add_argument("--service", default="/vlm/detect_objects",
                   help="Service name (default: /vlm/detect_objects)")
    p.add_argument("--timeout", type=float, default=30.0,
                   help="Service call timeout in seconds (default 30).")
    p.add_argument("--show", action="store_true",
                   help="Subscribe to the camera and draw bboxes on a frame.")
    p.add_argument("--image-topic", default="/oak/rgb/image_raw/compressed",
                   help="Image topic to use with --show.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    rclpy.init()

    client = VlmTestClient(args.service)
    response = client.call(args.prompt, timeout_sec=args.timeout)

    if response is None:
        client.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    print_response(response)

    if args.show:
        visualise(response, args.image_topic)

    client.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
