#!/usr/bin/env python3
from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image 
from rclpy.executors import MultiThreadedExecutor
from cv_bridge import CvBridge
import threading
import numpy as np
import tf2_ros
from scene_db import SceneDB, Detection
from geometry_msgs.msg import PointStamped
from tf2_geometry_msgs import do_transform_point
from rclpy.duration import Duration
from rclpy.callback_groups import ReentrantCallbackGroup


class LocalizerNode(Node):
    def __init__(self) -> None:
        super().__init__("localizer_node")
        
        # parameters
        self.declare_parameter("ticks_hz", 2.0)
        self.declare_parameter("world_frame", "world")
        self.declare_parameter("min_depth", 0.1)        # 10 cm
        self.declare_parameter("max_depth", 5.0)        # 5 m
        self.declare_parameter("window_size", 7)
        self.declare_parameter("depth_bins", 20)
        self.declare_parameter("depth_method", "histogram")
        
        self.ticks_hz = self.get_parameter("ticks_hz").get_parameter_value().double_value
        self.world_frame = self.get_parameter("world_frame").get_parameter_value().string_value
        self.min_depth = self.get_parameter("min_depth").get_parameter_value().double_value
        self.max_depth = self.get_parameter("max_depth").get_parameter_value().double_value
        self._window_size = self.get_parameter("window_size").get_parameter_value().integer_value
        self._depth_bins = self.get_parameter("depth_bins").get_parameter_value().integer_value
        self._depth_method = self.get_parameter("depth_method").get_parameter_value().string_value
        
        # variables
        self._depth = None
        self._depth_frame = None
        self._depth_lock = threading.Lock()
        self._fx = None
        self._fy = None
        self._cx = None
        self._cy = None
        self._info_w = None
        self._info_h = None
        
        # scene db
        self._db = SceneDB()
        
        # cv bridge
        self._bridge = CvBridge()
        
        # publishers, subscribers, timers and other
        self._cb_group = ReentrantCallbackGroup()
        
        self._cam_info_sub = self.create_subscription(
            CameraInfo, "/oak/stereo/camera_info", self._info_cb, 10, callback_group=self._cb_group
        )
        self._depth_sub = self.create_subscription(
            Image, "/oak/stereo/image_raw", self._depth_cb, 10, callback_group=self._cb_group
        )
        
        self._timer = self.create_timer(
            1.0 / self.ticks_hz, self._timer_cb, callback_group=self._cb_group
        )
        
        # tf2_ros
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)
        
        
        self.get_logger().info("LocalizerNode initialized")
        
        

    def _depth_cb(self, msg: Image) -> None:
        """Store depth image."""
        try:
            img = self._bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            self.get_logger().error(f"depth image decoding failed: {e}")
            return
        
        # convert to meters if uint16
        if img.dtype == np.uint16:
            depth_m = img.astype(np.float32) / 1000.0
        else:
            depth_m = img.astype(np.float32)
            
        with self._depth_lock:
            self._depth = depth_m
            self._depth_frame = msg.header.frame_id
            
    
    def _info_cb(self, msg: CameraInfo) -> None:
        """Read intrinsics once, then unsubscribe."""
        
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
        self.destroy_subscription(self._cam_info_sub)
        


    def _timer_cb(self) -> None:
        """Main tick."""
        if self._fx is None:
            return
        if self._depth is None:
            return
        
        with self._depth_lock:
            depth = self._depth.copy()
            depth_frame = self._depth_frame
            
        # get the rows with no world coordinates
        pending_rows = self._db.list_pending(limit= 20)
        if not pending_rows:
            return
        
        # loop over the pending rows
        for row in pending_rows:
            world_xyz = self._localize_row(row, depth, depth_frame)
            if world_xyz is None:
                continue
            # update the world coordinates in the database
            self._db.update_world_coords(row.id, world_xyz)
            
        
        
    def _localize_row(
        self, row: Detection, depth: np.ndarray, depth_frame: str
    ) -> tuple[float, float, float] | None:
        """Localize a row of detections."""
        depth_h, depth_w = depth.shape
        img_w, img_h = row.image_size
        x1, y1, x2, y2 = row.bbox
        
        # scale bbox into depth image coords
        du0 = int(x1 * depth_w / img_w)
        dv0 = int(y1 * depth_h / img_h)
        du1 = int(x2 * depth_w / img_w)
        dv1 = int(y2 * depth_h / img_h)

        # get depth Z and best pixel (u, v) from selected method
        if self._depth_method == "histogram":
            result = self._histogram_depth(depth, du0, dv0, du1, dv1)
        elif self._depth_method == "median":
            result = self._median_depth(depth, du0, dv0, du1, dv1)
        elif self._depth_method == "foreground":
            result = self._foreground_depth(depth, du0, dv0, du1, dv1)
        else:
            self.get_logger().warn(f"Unknown depth_method: {self._depth_method}")
            return None

        if result is None:
            return None
        Z, u, v = result

        if Z < self.min_depth or Z > self.max_depth:
            return None
        
        # back project pixel to camera 3d coordinates using intrinsics
        u_info = u * self._info_w / depth_w
        v_info = v * self._info_h / depth_h
        x_cam = (u_info - self._cx) * Z / self._fx
        y_cam = (v_info - self._cy) * Z / self._fy
        z_cam = Z
        
        # build a transform message
        pt = PointStamped()
        pt.header.frame_id = depth_frame
        pt.header.stamp = self.get_clock().now().to_msg()
        pt.point.x = x_cam
        pt.point.y = y_cam
        pt.point.z = z_cam
        
        # transform the point to world frame
        try:
            tf_msg = self._tf_buffer.lookup_transform(
                self.world_frame, 
                depth_frame, 
                rclpy.time.Time(),
                timeout=Duration(seconds=0.2)
            )
            pt_world = do_transform_point(pt, tf_msg)
        except tf2_ros.TransformException as e:
            self.get_logger().warn(
                f"TF {self.world_frame} ← {depth_frame} failed: {e}",
                throttle_duration_sec=5.0,
            )
            return None
        
        return (pt_world.point.x, pt_world.point.y, pt_world.point.z) 
        
        
    
    def _best_pixel(
        self, patch: np.ndarray, mask: np.ndarray, Z: float, u0: int, v0: int
    ) -> tuple[float, int, int]:
        """Return (Z, u_abs, v_abs) — pixel in patch closest to Z."""
        diff = np.abs(patch - Z)
        diff[~mask] = np.inf
        best = np.unravel_index(np.argmin(diff), diff.shape)
        return (Z, u0 + best[1], v0 + best[0])

    def _median_depth(
        self, depth: np.ndarray, u0: int, v0: int, u1: int, v1: int
    ) -> tuple[float, int, int] | None:
        """Median depth in NxN patch around bbox center + best pixel."""
        depth_h, depth_w = depth.shape
        uc = (u0 + u1) // 2
        vc = (v0 + v1) // 2
        half = self._window_size // 2
        pu0, pu1 = max(0, uc - half), min(depth_w, uc + half + 1)
        pv0, pv1 = max(0, vc - half), min(depth_h, vc + half + 1)
        patch = depth[pv0:pv1, pu0:pu1]
        mask = np.isfinite(patch) & (patch > 0.0)
        if not np.any(mask):
            return None
        Z = float(np.median(patch[mask]))
        return self._best_pixel(patch, mask, Z, pu0, pv0)
        
        
    def _foreground_depth(
        self, depth: np.ndarray, u0: int, v0: int, u1: int, v1: int
    ) -> tuple[float, int, int] | None:
        """15th percentile depth inside bbox + best pixel."""
        patch = depth[v0:v1, u0:u1]
        mask = np.isfinite(patch) & (patch > 0.0)
        if not mask.any():
            return None
        Z = float(np.percentile(patch[mask], 15))
        return self._best_pixel(patch, mask, Z, u0, v0)

    def _histogram_depth(
        self, depth: np.ndarray, u0: int, v0: int, u1: int, v1: int
    ) -> tuple[float, int, int] | None:
        """First dominant depth bin (>10% of valid pixels) + best pixel."""
        patch = depth[v0:v1, u0:u1]
        mask = np.isfinite(patch) & (patch > 0.0)
        if not mask.any():
            return None
        valid = patch[mask]
        counts, bin_edges = np.histogram(valid, bins=self._depth_bins)
        threshold = 0.10 * len(valid)
        for i, count in enumerate(counts):
            if count > threshold:
                Z = float(0.5 * (bin_edges[i] + bin_edges[i + 1]))
                return self._best_pixel(patch, mask, Z, u0, v0)
        return None

                
        
        
        



def main(args=None) -> None:
    rclpy.init(args=args)
    node = LocalizerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    
    node.destroy_node()
    

    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
