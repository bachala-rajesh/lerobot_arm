#!/usr/bin/env python3
"""
Fix the gz (Ignition) depth camera_info — SIM only.

Problem: gz rgbd_camera publishes a camera_info whose P (projection) matrix keeps
the DEFAULT 320x240 intrinsics, even though the image is 640x480 and K is correct.
depth_image_proc deprojects using P, so the point cloud comes out shifted.

Fix: for a camera with no rectification/distortion, P must equal [K | 0]. This
node copies the (correct) K into P and republishes the camera_info, keeping the
original timestamp so it still syncs with the depth image.

  in : /oak/stereo/camera_info        (gz, wrong P)
  out: /oak/stereo/camera_info_fixed  (correct P)
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo


class CameraInfoFixer(Node):
    def __init__(self) -> None:
        super().__init__("camera_info_fixer")
        self.declare_parameter("in_topic", "/oak/stereo/camera_info")
        self.declare_parameter("out_topic", "/oak/stereo/camera_info_fixed")
        in_topic = self.get_parameter("in_topic").get_parameter_value().string_value
        out_topic = self.get_parameter("out_topic").get_parameter_value().string_value

        self.pub = self.create_publisher(CameraInfo, out_topic, 10)
        self.sub = self.create_subscription(CameraInfo, in_topic, self.callback, 10)
        self.get_logger().info(f"Fixing camera_info: {in_topic} -> {out_topic}")

    def callback(self, msg: CameraInfo) -> None:
        k = msg.k  # 3x3 row-major: fx 0 cx / 0 fy cy / 0 0 1
        # P (3x4) = [K | 0] when there is no rectification/distortion.
        msg.p = [
            k[0], k[1], k[2], 0.0,
            k[3], k[4], k[5], 0.0,
            k[6], k[7], k[8], 0.0,
        ]
        self.pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = CameraInfoFixer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
