#!/usr/bin/env python3
"""
apriltag_world_localizer.py

Compute camera pose in world frame from known tag poses + apriltag detections.

Inputs:
  - YAML config: known tag poses in world frame
  - TF: camera -> tag (from apriltag_node)

Output:
  - TF: world -> oak_rgb_camera_link
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
import tf2_ros
from geometry_msgs.msg import TransformStamped

import numpy as np
from tf_transformations import quaternion_matrix, quaternion_from_matrix, euler_matrix
import yaml


class AprilTagWorldLocalizer(Node):
    def __init__(self) -> None:
        super().__init__("apriltag_world_localizer")

        # ----- Parameters -----
        self.declare_parameter("config_file_path", "")
        self.config_file_path = (
            self.get_parameter("config_file_path").get_parameter_value().string_value
        )

        if not self.config_file_path:
            self.get_logger().error("config_file_path is empty")
            raise ValueError("config_file_path is empty")
        else:
            self.get_logger().info(
                f"reading parameter file path from the file: {self.config_file_path}"
            )

        self._load_config()

        # ----- TF -----
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)
        self._tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Cache the static link <- optical transform once we get it
        self._T_link_optical: np.ndarray | None = None

        # ----- Timer -----
        self._timer_period = self.create_timer(
            1.0 / self._update_rate, self.compute_and_publish
        )

        self.get_logger().info("AprilTagWorldLocalizer started")

    # ===================================================
    # Helper functions — pure math
    # ===================================================

    def _load_config(self) -> None:
        """Load YAML config file."""
        with open(self.config_file_path, "r") as f:
            cfg = yaml.safe_load(f)

        self._world_frame: str = cfg["world_frame"]
        self._camera_frame: str = cfg["camera_frame"]
        self._camera_optical_frame: str = cfg["camera_optical_frame"]
        self._update_rate: float = cfg["update_rate"]

        tag_specs: dict = cfg["tags"]

        # convert each tag pose to 4x4 matrix
        self.known_tag_transforms: dict[str, np.ndarray] = {}
        for tag_id, pose in tag_specs.items():
            self.known_tag_transforms[tag_id] = self.pose_to_matrix(*pose)

        self.get_logger().info(
            f"loaded {len(self.known_tag_transforms)} known tag transforms from config file {self.config_file_path}"
        )

    def pose_to_matrix(
        self, x: float, y: float, z: float, roll: float, pitch: float, yaw: float
    ) -> np.ndarray:
        """Build 4x4 homogeneous transform from xyz + rpy (radians)."""
        mat = euler_matrix(roll, pitch, yaw)  # 4x4 with identity translation
        mat[0, 3] = x
        mat[1, 3] = y
        mat[2, 3] = z
        return mat

    def transform_msg_to_matrix(self, t: TransformStamped) -> np.ndarray:
        """Convert geometry_msgs/TransformStamped to 4x4 numpy matrix."""
        q = t.transform.rotation
        mat = quaternion_matrix([q.x, q.y, q.z, q.w])
        mat[0, 3] = t.transform.translation.x
        mat[1, 3] = t.transform.translation.y
        mat[2, 3] = t.transform.translation.z
        return mat

    def matrix_to_transform_msg(
        self, mat: np.ndarray, parent_frame: str, child_frame: str
    ) -> TransformStamped:
        """Convert 4x4 numpy matrix to TransformStamped ready to broadcast."""
        msg = TransformStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = parent_frame
        msg.child_frame_id = child_frame
        msg.transform.translation.x = float(mat[0, 3])
        msg.transform.translation.y = float(mat[1, 3])
        msg.transform.translation.z = float(mat[2, 3])
        q = quaternion_from_matrix(mat)
        msg.transform.rotation.x = float(q[0])
        msg.transform.rotation.y = float(q[1])
        msg.transform.rotation.z = float(q[2])
        msg.transform.rotation.w = float(q[3])
        return msg

    # ===================================================
    # TF helpers
    # ===================================================

    def _ensure_link_optical_cached(self) -> bool:
        """Look up static camera_link <- camera_optical_frame once and cache."""
        if self._T_link_optical is not None:
            return True
        try:
            tf_msg = self._tf_buffer.lookup_transform(
                self._camera_frame,  # target: link
                self._camera_optical_frame,  # source: optical
                rclpy.time.Time(),
            )
        except tf2_ros.TransformException as e:
            self.get_logger().warn(
                f"Waiting for {self._camera_frame} <- {self._camera_optical_frame}: {e}",
                throttle_duration_sec=2.0,
            )
            return False
        self._T_link_optical = self.transform_msg_to_matrix(tf_msg)
        self.get_logger().info("Cached camera_link <- optical_frame transform")
        return True

    # ===================================================
    # Main compute loop
    # ===================================================

    def compute_and_publish(self) -> None:
        """
        For each known tag:
          1. Look up TF camera_optical -> tag (from apriltag_node)
          2. Compute T_world_optical = T_world_tag * inverse(T_optical_tag)
          3. Convert to T_world_link via cached link <- optical
        Fuse estimates -> single T_world_link
        Broadcast TF world -> camera_link
        """
        if not self._ensure_link_optical_cached():
            return

        estimates: list[np.ndarray] = []

        for tag_frame, T_world_tag in self.known_tag_transforms.items():
            try:
                tf_msg = self._tf_buffer.lookup_transform(
                    self._camera_optical_frame,  # target
                    tag_frame,  # source
                    rclpy.time.Time(),
                )
            except tf2_ros.TransformException:
                continue

            T_optical_tag = self.transform_msg_to_matrix(tf_msg)

            # T_world_optical = T_world_tag * inverse(T_optical_tag)
            T_world_optical = T_world_tag @ np.linalg.inv(T_optical_tag)

            # T_world_link = T_world_optical * inverse(T_link_optical)
            T_world_link = T_world_optical @ np.linalg.inv(self._T_link_optical)

            estimates.append(T_world_link)

        if not estimates:
            self.get_logger().warn(
                "No known tags visible — cannot publish camera TF",
                throttle_duration_sec=2.0,
            )
            return

        fused = self.fuse_estimates(estimates)
        msg = self.matrix_to_transform_msg(fused, self._world_frame, self._camera_frame)
        self._tf_broadcaster.sendTransform(msg)

    def fuse_estimates(self, estimates: list[np.ndarray]) -> np.ndarray:
        """Average translations + quaternions across multiple estimates."""
        if len(estimates) == 1:
            return estimates[0]

        # Average translation
        translations = np.array([m[:3, 3] for m in estimates])
        t_avg = translations.mean(axis=0)

        # Average quaternion (sign-align to avoid cancellation)
        quats: list[np.ndarray] = []
        ref: np.ndarray | None = None
        for m in estimates:
            q = np.array(quaternion_from_matrix(m))
            if ref is None:
                ref = q
            elif np.dot(ref, q) < 0.0:
                q = -q
            quats.append(q)
        q_avg = np.mean(quats, axis=0)
        q_avg = q_avg / np.linalg.norm(q_avg)

        # Rebuild matrix
        mat = quaternion_matrix(q_avg)
        mat[0, 3] = t_avg[0]
        mat[1, 3] = t_avg[1]
        mat[2, 3] = t_avg[2]
        return mat


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AprilTagWorldLocalizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
