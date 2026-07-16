#!/usr/bin/env python3
"""ROS2 node: OAK-D point cloud + AnyGrasp, exposed as a service.

Flow:
  1. subscribe /oak/points, keep only the latest message
  2. on a Trigger service call:
       latest cloud -> numpy (xyz + rgb) -> drop NaN
       -> AnyGraspModel.predict() -> grasp poses
       -> Open3D window (cloud + grippers)
       -> reply success + "N grasps, best <score>"

Run inside the anygrasp env (conda on laptop / robotics_layer2 docker), because
it imports gsnet + torch through anygrasp_model. See
src/z_usage_new_tools/using_anygrasp_model.md for the env setup.

  ros2 run segment_grasppose grasppose_server
  ros2 service call /find_grasp_pose std_srvs/srv/Trigger

Offline check of the rgb unpack (no ROS needed):
  python3 grasppose_server_node.py --selfcheck
"""

from __future__ import annotations

import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener

# AnyGraspModel / _show imported lazily inside the node — see __init__.
# Keeping them out of module scope lets --selfcheck (pure numpy) run anywhere.

CLOUD_TOPIC = "/oak/points"
SERVICE = "/find_grasp_pose"
TAG_FRAME = "tag36h11:1"  # AprilTag on the table; its +Z is the table normal


def unpack_rgb(rgb_field: np.ndarray) -> np.ndarray:
    """Packed rgb field -> (N, 3) float32 in 0..1.

    depth_image_proc packs colour as 0x00RRGGBB inside one 32-bit slot. The
    field usually arrives typed as float32, so we reinterpret the bytes as
    uint32 (view, not cast) before pulling the channels apart.
    """
    packed = np.ascontiguousarray(rgb_field)
    if packed.dtype != np.uint32:
        packed = packed.view(np.uint32)
    r = (packed >> 16) & 0xFF
    g = (packed >> 8) & 0xFF
    b = packed & 0xFF
    # ponytail: assumes RRGGBB order. If the window shows swapped colours,
    # swap r<->b here — display only, grasp poses are unaffected.
    return np.stack([r, g, b], axis=1).astype(np.float32) / 255.0


def cloud_to_numpy(cloud: PointCloud2) -> tuple[np.ndarray, np.ndarray]:
    """PointCloud2 (XYZRGB) -> points (N, 3) float32, colors (N, 3) float32.

    skip_nans drops the holes an organized cloud carries, keeping xyz and rgb
    row-aligned. AnyGrasp chokes on NaN, so this must happen before predict().
    """
    arr = point_cloud2.read_points(
        cloud, field_names=("x", "y", "z", "rgb"), skip_nans=True
    )
    xyz = np.column_stack([arr["x"], arr["y"], arr["z"]]).astype(np.float32)
    colors = unpack_rgb(arr["rgb"])
    return xyz, colors


class GraspPoseServer(Node):
    """Holds the AnyGrasp model, runs it on demand against the latest cloud."""

    def __init__(self) -> None:
        super().__init__("grasppose_server")
        self._latest: PointCloud2 | None = None

        # tunable without a rebuild: which tag marks the table, and how much to
        # keep above it (0.0 = cut at the table, 0.01 = also strip its surface).
        self._tag_frame = self.declare_parameter("table_tag_frame", TAG_FRAME).value
        self._min_height = self.declare_parameter("table_min_height", 0.0).value

        # TF: to look up the tag's pose in the cloud frame at request time.
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        # Match the publisher: /oak/points is BEST_EFFORT, KEEP_LAST 5, VOLATILE
        # (checked with `ros2 topic info /oak/points -v`). A reliable sub would
        # not connect to a best-effort publisher at all.
        self.create_subscription(
            PointCloud2, CLOUD_TOPIC, self._on_cloud, qos_profile_sensor_data
        )
        self.create_service(Trigger, SERVICE, self._on_request)

        from segment_grasppose.anygrasp_model import AnyGraspModel

        self.get_logger().info("loading AnyGrasp (slow, once)...")
        self._model = AnyGraspModel()
        self.get_logger().info(
            f"ready. cloud={CLOUD_TOPIC}  "
            f"call: ros2 service call {SERVICE} std_srvs/srv/Trigger"
        )

    def _on_cloud(self, msg: PointCloud2) -> None:
        self._latest = msg

    def _lookup_tag(
        self, cloud_frame: str
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """Tag pose (translation, quat xyzw) in the cloud frame, or (None, None).

        None -> the tag was not seen; table removal is skipped and we go on.
        """
        try:
            tf = self._tf_buffer.lookup_transform(
                cloud_frame, self._tag_frame, Time()
            )
        except Exception as exc:  # tag not visible / TF not up yet
            self.get_logger().warn(
                f"no TF {self._tag_frame} -> {cloud_frame}; "
                f"skipping table removal ({exc})"
            )
            return None, None
        t = tf.transform.translation
        q = tf.transform.rotation
        return (
            np.array([t.x, t.y, t.z], dtype=np.float32),
            np.array([q.x, q.y, q.z, q.w], dtype=np.float32),
        )

    def _on_request(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        cloud = self._latest
        if cloud is None:
            response.success = False
            response.message = f"no cloud on {CLOUD_TOPIC} yet"
            self.get_logger().warn(response.message)
            return response

        from segment_grasppose.cloud_processing import clean_cloud

        points, colors = cloud_to_numpy(cloud)
        tag_t, tag_q = self._lookup_tag(cloud.header.frame_id)
        points, colors = clean_cloud(
            points, colors, tag_t, tag_q, self._min_height
        )
        self.get_logger().info(f"cloud after cleaning: {len(points)} points")

        # lims=None -> box derived from the whole cloud (raw scene, "as is").
        gg = self._model.predict(points, colors)
        if gg is None:
            response.success = False
            response.message = "no grasp found (raw scene — try cropping / lims)"
            self.get_logger().warn(response.message)
            return response

        response.success = True
        response.message = f"{len(gg)} grasps, best {gg[0].score:.3f}"
        self.get_logger().info(response.message)

        # Blocks until the window is closed. The service reply waits for that.
        # Fine for a test tool; the node is frozen while the window is open.
        from segment_grasppose.anygrasp_model import _show

        _show(gg, points, colors)
        return response


def _selfcheck() -> None:
    """Offline: the rgb unpack is the only tricky bit, so prove it alone."""
    packed = np.array([0x00FF8000], dtype=np.uint32).view(np.float32)
    out = unpack_rgb(packed)
    assert np.allclose(out[0], [1.0, 128 / 255, 0.0]), out
    print("rgb unpack OK")


def main() -> None:
    rclpy.init()
    node = GraspPoseServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        main()
