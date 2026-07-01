#!/usr/bin/env python3
"""
Grasp pose estimation node — SAM2 + AnyGrasp pipeline.

Subscribes:
  image_topic       (sensor_msgs/Image)      default: /oak/rgb/image_raw
  pointcloud_topic  (sensor_msgs/PointCloud2) default: /oak/points

Service:
  /segment_grasppose/find_grasp_pose  (so101_interfaces/srv/FindGraspPose)

Pipeline (stubs — wire models in TODO sections):
  1. Resolve bboxes from request.bboxes_xyxy OR scene_db query by object_label
  2. SAM2(image, bboxes) → mask (H, W bool)
  3. Filter point cloud by mask → masked_pc (N, 3)
  4. AnyGrasp(masked_pc) → grasp_poses
  5. Return ranked poses
"""
from __future__ import annotations

import threading
from typing import Optional

import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image, PointCloud2
from sensor_msgs_py import point_cloud2 as pc2

from so101_interfaces.srv import FindGraspPose


class SegmentGraspPoseNode(Node):
    def __init__(self) -> None:
        super().__init__('segment_grasppose_node')

        self.declare_parameter('image_topic', '/oak/rgb/image_raw')
        self.declare_parameter('pointcloud_topic', '/oak/points')

        image_topic: str = self.get_parameter('image_topic').get_parameter_value().string_value
        pc_topic: str = self.get_parameter('pointcloud_topic').get_parameter_value().string_value

        self._bridge = CvBridge()
        self._lock = threading.Lock()
        self._latest_image: Optional[Image] = None
        self._latest_cloud: Optional[PointCloud2] = None

        # TODO: load SAM2 model here
        # from sam2.build_sam import build_sam2
        # self._sam2 = build_sam2(...)

        # TODO: load AnyGrasp model here
        # from anygrasp_sdk import AnyGraspDetector
        # self._anygrasp = AnyGraspDetector(...)

        cb_group = ReentrantCallbackGroup()

        self.create_subscription(Image, image_topic, self._image_cb, 10, callback_group=cb_group)
        self.create_subscription(PointCloud2, pc_topic, self._cloud_cb, 10, callback_group=cb_group)

        self.create_service(
            FindGraspPose,
            '/segment_grasppose/find_grasp_pose',
            self._find_grasp_cb,
            callback_group=cb_group,
        )

        self.get_logger().info(f'Subscribed to: {image_topic}')
        self.get_logger().info(f'Subscribed to: {pc_topic}')
        self.get_logger().info('Service ready: /segment_grasppose/find_grasp_pose')

    # ── subscriber callbacks ───────────────────────────────────────────────────

    def _image_cb(self, msg: Image) -> None:
        with self._lock:
            self._latest_image = msg

    def _cloud_cb(self, msg: PointCloud2) -> None:
        with self._lock:
            self._latest_cloud = msg

    # ── service handler ────────────────────────────────────────────────────────

    def _find_grasp_cb(
        self,
        request: FindGraspPose.Request,
        response: FindGraspPose.Response,
    ) -> FindGraspPose.Response:

        with self._lock:
            image = self._latest_image
            cloud = self._latest_cloud

        if image is None or cloud is None:
            response.success = False
            response.message = 'No image or point cloud received yet'
            return response

        # ── Step 1: resolve bboxes ─────────────────────────────────────────────
        bboxes = np.array(request.bboxes_xyxy, dtype=np.float64).reshape(-1, 4)

        if bboxes.size == 0:
            if not request.object_label:
                response.success = False
                response.message = 'Provide bboxes_xyxy or object_label'
                return response

            # TODO: query scene_db for latest bbox of this object
            # from scene_db import SceneDB
            # rows = SceneDB().query_recent(label=request.object_label, limit=1)
            # bboxes = np.array([[r.x1, r.y1, r.x2, r.y2] for r in rows])
            self.get_logger().info(f'scene_db query stub: label="{request.object_label}"')
            response.success = False
            response.message = 'scene_db query not wired yet'
            return response

        self.get_logger().info(f'Using {len(bboxes)} bbox(es)')

        # ── Step 2: SAM2 → mask ────────────────────────────────────────────────
        mask = self._run_sam2(image, bboxes)   # (H, W) bool

        # ── Step 3: filter point cloud by mask ────────────────────────────────
        filtered_pc = self._filter_pointcloud(cloud, mask)  # (N, 3)
        self.get_logger().info(f'Filtered PC: {len(filtered_pc)} points')

        if len(filtered_pc) == 0:
            response.success = False
            response.message = 'Empty point cloud after masking'
            return response

        # ── Step 4: AnyGrasp → poses ───────────────────────────────────────────
        grasp_poses = self._run_anygrasp(filtered_pc, image.header)

        response.success = True
        response.message = f'{len(grasp_poses)} grasp pose(s) found'
        response.grasp_poses = grasp_poses
        return response

    # ── pipeline steps ─────────────────────────────────────────────────────────

    def _run_sam2(self, image: Image, bboxes: np.ndarray) -> np.ndarray:
        """Return (H, W) bool mask. bboxes shape: (N, 4) in [x1,y1,x2,y2] pixel coords."""
        # TODO: wire real SAM2 inference
        # cv_img = self._bridge.imgmsg_to_cv2(image, 'bgr8')
        # with torch.inference_mode():
        #     self._sam2.set_image(cv_img)
        #     masks, _, _ = self._sam2.predict(box=bboxes, multimask_output=False)
        # return masks[0].astype(bool)  # (H, W)
        self.get_logger().warn('SAM2 stub: returning empty mask')
        return np.zeros((image.height, image.width), dtype=bool)

    def _run_anygrasp(self, pc: np.ndarray, header) -> list:
        """Return list of geometry_msgs/PoseStamped, best first. pc shape: (N, 3)."""
        # TODO: wire real AnyGrasp inference
        # xmin, ymin, zmin = pc.min(axis=0)
        # xmax, ymax, zmax = pc.max(axis=0)
        # locs, dirs, scores, _ = self._anygrasp.get_grasps(
        #     pc, xmin, xmax, ymin, ymax, zmin, zmax
        # )
        # return [_grasp_to_pose_stamped(l, d, header) for l, d in zip(locs, dirs)]
        self.get_logger().warn('AnyGrasp stub: returning no poses')
        return []

    def _filter_pointcloud(self, cloud: PointCloud2, mask: np.ndarray) -> np.ndarray:
        """Return (N, 3) float32 array of points inside mask.

        Assumes organized PC (cloud.height == mask.shape[0]).
        Returns empty array if shapes don't match (unorganized PC not supported yet).
        """
        pts = np.array(
            list(pc2.read_points(cloud, field_names=('x', 'y', 'z'), skip_nans=False)),
            dtype=np.float32,
        )  # (H*W, 3)

        if cloud.height == mask.shape[0] and cloud.width == mask.shape[1]:
            pts_3d = pts.reshape(cloud.height, cloud.width, 3)
            valid_depth = ~np.isnan(pts_3d[:, :, 2])
            return pts_3d[mask & valid_depth]
        else:
            self.get_logger().warn(
                f'PC size ({cloud.height}x{cloud.width}) != mask ({mask.shape}). '
                'Unorganized PC not supported — returning empty.'
            )
            return np.empty((0, 3), dtype=np.float32)


# ── helpers ────────────────────────────────────────────────────────────────────

# def _grasp_to_pose_stamped(location, direction, header):
#     from geometry_msgs.msg import PoseStamped, Point, Quaternion
#     import tf_transformations
#     ps = PoseStamped()
#     ps.header = header
#     ps.pose.position = Point(x=float(location[0]), y=float(location[1]), z=float(location[2]))
#     # convert grasp direction to quaternion here
#     return ps


def main() -> None:
    rclpy.init()
    node = SegmentGraspPoseNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
