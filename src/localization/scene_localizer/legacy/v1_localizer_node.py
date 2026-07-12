#!/usr/bin/env python3
"""Scene Localizer — fills 3D world coords for pending detections.

Flow per tick:
  1. db.list_pending(batch_limit)
  2. for each row:
       a. scale bbox center into depth image space
       b. take NxN median depth
       c. back-project pixel + depth → 3D point in camera (depth) frame
       d. tf-transform → world frame
       e. db.update_world_coords(row.id, world_xyz)

Assumes:
  - The depth topic is aligned to the SAME camera as the bbox source
    (e.g. OAK-D RGB-aligned depth).
  - apriltags_localization broadcasts world → oak_rgb_camera_link, and
    URDF supplies camera_link → optical_frame statically, so tf2 can
    resolve world ← depth.header.frame_id automatically.
"""
from __future__ import annotations

import threading

import numpy as np
import rclpy
import tf2_ros
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.duration import Duration
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from tf2_geometry_msgs import do_transform_point

from scene_db import Detection, SceneDB


class LocalizerNode(Node):
    def __init__(self) -> None:
        super().__init__("localizer_node")

        # ----- params -----
        self.declare_parameter("depth_topic", "/oak/stereo/image_raw")
        self.declare_parameter("camera_info_topic", "/oak/stereo/camera_info")
        self.declare_parameter("world_frame", "world")
        self.declare_parameter("tick_hz", 2.0)
        self.declare_parameter("batch_limit", 20)
        self.declare_parameter("patch_size", 7)
        self.declare_parameter("min_depth", 0.1)
        self.declare_parameter("max_depth", 5.0)
        self.declare_parameter("tf_timeout_sec", 0.2)

        gp = self.get_parameter
        self._depth_topic: str = gp("depth_topic").get_parameter_value().string_value
        self._info_topic: str = gp("camera_info_topic").get_parameter_value().string_value
        self._world_frame: str = gp("world_frame").get_parameter_value().string_value
        self._tick_hz: float = gp("tick_hz").get_parameter_value().double_value
        self._batch_limit: int = gp("batch_limit").get_parameter_value().integer_value
        self._patch: int = gp("patch_size").get_parameter_value().integer_value
        self._min_d: float = gp("min_depth").get_parameter_value().double_value
        self._max_d: float = gp("max_depth").get_parameter_value().double_value
        self._tf_timeout = Duration(
            seconds=gp("tf_timeout_sec").get_parameter_value().double_value
        )

        # ----- state -----
        self._bridge = CvBridge()
        self._db = SceneDB()
        self.get_logger().info(f"scene_db opened at {self._db.path}")

        self._depth: np.ndarray | None = None     # meters, float32
        self._depth_frame: str | None = None
        self._depth_lock = threading.Lock()

        self._fx: float | None = None
        self._fy: float | None = None
        self._cx: float | None = None
        self._cy: float | None = None
        self._info_w: int | None = None
        self._info_h: int | None = None

        # ----- tf -----
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        # ----- subs + timer -----
        cb = ReentrantCallbackGroup()
        self._depth_sub = self.create_subscription(
            Image, self._depth_topic, self._depth_cb, 10, callback_group=cb
        )
        self._info_sub = self.create_subscription(
            CameraInfo, self._info_topic, self._info_cb, 10, callback_group=cb
        )
        self._timer = self.create_timer(
            1.0 / self._tick_hz, self._tick, callback_group=cb
        )

        self.get_logger().info(
            f"LocalizerNode ready — depth: {self._depth_topic}, "
            f"world_frame: {self._world_frame}, tick: {self._tick_hz} Hz"
        )

    # -------------------------------------------------- callbacks
    def _depth_cb(self, msg: Image) -> None:
        """Decode depth image and cache as float32 meters."""
        try:
            img = self._bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            self.get_logger().error(f"depth decode failed: {e}")
            return

        if img.dtype == np.uint16:
            # OAK-D default: millimeters → meters
            depth_m = img.astype(np.float32) * 0.001
        else:
            depth_m = img.astype(np.float32)

        with self._depth_lock:
            self._depth = depth_m
            self._depth_frame = msg.header.frame_id

    def _info_cb(self, msg: CameraInfo) -> None:
        """Read intrinsics once, then unsubscribe."""
        if self._fx is not None:
            return
        self._fx = msg.k[0]
        self._fy = msg.k[4]
        self._cx = msg.k[2]
        self._cy = msg.k[5]
        self._info_w = msg.width
        self._info_h = msg.height
        self.get_logger().info(
            f"Intrinsics: fx={self._fx:.1f} fy={self._fy:.1f} "
            f"cx={self._cx:.1f} cy={self._cy:.1f} ({self._info_w}x{self._info_h})"
        )
        self.destroy_subscription(self._info_sub)

    # -------------------------------------------------- main tick
    def _tick(self) -> None:
        if self._fx is None:
            self.get_logger().warn(
                "Waiting for camera_info...", throttle_duration_sec=5.0
            )
            return

        with self._depth_lock:
            depth = None if self._depth is None else self._depth.copy()
            depth_frame = self._depth_frame

        if depth is None or depth_frame is None:
            self.get_logger().warn(
                "Waiting for depth image...", throttle_duration_sec=5.0
            )
            return

        pending = self._db.list_pending(limit=self._batch_limit)
        if not pending:
            return

        ok, skipped = 0, 0
        for row in pending:
            world_xyz = self._localize_row(row, depth, depth_frame)
            if world_xyz is None:
                skipped += 1
                continue
            self._db.update_world_coords(row.id, world_xyz)
            ok += 1

        if ok or skipped:
            self.get_logger().info(
                f"tick: localized {ok}, skipped {skipped}, "
                f"pending {len(pending)}"
            )

    # -------------------------------------------------- per-row math
    def _localize_row(
        self,
        row: Detection,
        depth: np.ndarray,
        depth_frame: str,
    ) -> tuple[float, float, float] | None:
        """Return world_xyz or None if the row can't be localized this tick."""
        depth_h, depth_w = depth.shape
        img_w, img_h = row.image_size
        x1, y1, x2, y2 = row.bbox

        # bbox center in original image coords → depth image coords
        u_orig = 0.5 * (x1 + x2)
        v_orig = 0.5 * (y1 + y2)
        u = int(u_orig * depth_w / img_w)
        v = int(v_orig * depth_h / img_h)
        if not (0 <= u < depth_w and 0 <= v < depth_h):
            return None

        Z = self._median_depth(depth, u, v)
        if Z is None or not (self._min_d < Z < self._max_d):
            return None

        # back-project pixel → camera (depth) frame
        # NOTE: intrinsics are from camera_info, which is for the depth image
        # at info_w×info_h. Scale (u,v) and (cx,cy) into that space.
        u_info = u * self._info_w / depth_w
        v_info = v * self._info_h / depth_h
        x_cam = (u_info - self._cx) * Z / self._fx
        y_cam = (v_info - self._cy) * Z / self._fy
        z_cam = Z

        # tf: depth_frame → world
        pt = PointStamped()
        pt.header.frame_id = depth_frame
        pt.header.stamp = rclpy.time.Time().to_msg()  # latest available
        pt.point.x, pt.point.y, pt.point.z = float(x_cam), float(y_cam), float(z_cam)

        try:
            tf_msg = self._tf_buffer.lookup_transform(
                self._world_frame,
                depth_frame,
                rclpy.time.Time(),
                timeout=self._tf_timeout,
            )
            pt_world = do_transform_point(pt, tf_msg)
        except tf2_ros.TransformException as e:
            self.get_logger().warn(
                f"TF {self._world_frame} ← {depth_frame} failed: {e}",
                throttle_duration_sec=5.0,
            )
            return None

        return (pt_world.point.x, pt_world.point.y, pt_world.point.z)

    # -------------------------------------------------- helpers
    def _median_depth(
        self, depth: np.ndarray, u: int, v: int
    ) -> float | None:
        """Median of an NxN patch around (u, v), ignoring zeros and NaNs."""
        half = self._patch // 2
        h, w = depth.shape
        u0, u1 = max(0, u - half), min(w, u + half + 1)
        v0, v1 = max(0, v - half), min(h, v + half + 1)
        patch = depth[v0:v1, u0:u1]
        mask = np.isfinite(patch) & (patch > 0.0)
        if not mask.any():
            return None
        return float(np.median(patch[mask]))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LocalizerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    node._db.close()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
