#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from apriltag_msgs.msg import AprilTagDetectionArray
from geometry_msgs.msg import Pose, TransformStamped
import numpy as np
from cv_bridge import CvBridge
from typing import Optional
from dt_apriltags import Detector
import sys
import cv2
from tf2_ros import TransformBroadcaster
from scipy.spatial.transform import Rotation
import yaml
from pathlib import Path
from ament_index_python import get_package_share_directory
from scipy.spatial.transform import Rotation
from apriltag_msgs.msg import AprilTagDetectionArray
import cv2
from sensor_msgs.msg import CameraInfo
from scipy.spatial.transform import Rotation


class OptimizePose(Node):
    def __init__(self):
        super().__init__("optimize_pose_node")

        # declare parameters
        self.declare_parameter("global_tags_location_filename", "")

        # Publisher
        # self.publisher = self.create_publisher(Pose, '/pose_apriltags', 10)

        # Subscribers
        self.tag_detections_sub = self.create_subscription(
            AprilTagDetectionArray, "/detections", self.detections_callback, 10
        )
        self.camera_info_sub = self.create_subscription(CameraInfo, "/camera_info", self.camera_info_callback, 10)

        # Timer
        timer_period_sec: float = 0.5
        self.timer = self.create_timer(timer_period_sec, self.timer_callback)

        # global variables
        self.tag_global_corners = {}
        self.global_tags_location_filename = None
        self.detected_img_corners = []
        self.detected_global_corners = []
        self.K = None  # camera intrinsic matrix
        self.camera_frame_id = "camera_optical_frame"
        self.dist_coeffs = None
        self.n_detected_tags = 0

        # get the params
        self.get_params()

        # get the global apriltags location
        self.read_global_locations_from_file(self.global_tags_location_filename)

        self.get_logger().info("optimize pose from april tags node initialized and running ✅")

    def get_params(self):
        self.global_tags_location_filename = (
            self.get_parameter("global_tags_location_filename").get_parameter_value().string_value
        )

    def read_global_locations_from_file(self, file_name):
        # get the proper file path for the given file
        try:
            pkg_path = Path(get_package_share_directory("apriltags_localization"))
            file_path = pkg_path / "config" / file_name
        except Exception as e:
            self.get_logger().error(f"Could not get the proper package path for the{file_name}... {str(e)}")

        # read the data from the yaml file
        try:
            with open(file_path, "r") as file:
                data = yaml.safe_load(file)
                self.get_tags_global_locations(data)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAML file not found: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {str(e)}")

    def get_tags_global_locations(self, yaml_data):
        yaml_data = yaml_data.get("apriltags", {})

        for tag_info in yaml_data.values():
            tag_edge_length = tag_info["size"]
            tag_id = tag_info["id"]
            tag_position = tag_info["position"]
            tag_orientation = tag_info["orientation"]
            corners = self.get_tags_corners_world(tag_position, tag_orientation, tag_edge_length)

            # add the tag_id and the corners to the tag_global_corners
            self.tag_global_corners[tag_id] = corners

    def get_tags_corners_world(self, tag_position, tag_orientation, tag_edge_length):
        half = tag_edge_length / 2
        corners_local = np.array(
            [
                [-half, half, 0.0],  # top-left
                [half, half, 0.0],  # top-right
                [half, -half, 0.0],  # bottom-right
                [-half, -half, 0.0],  # bottom-left
            ]
        )  # shape (4,3)

        # convert RPY to rotation matrix
        r = Rotation.from_euler(
            "xyz", [tag_orientation["roll"], tag_orientation["pitch"], tag_orientation["yaw"]], degrees=False
        )
        rotation_matrix = r.as_matrix()

        # translation matrix
        translation = np.array([tag_position["x"], tag_position["y"], tag_position["z"]])  # shape (3,)

        # get corners
        corners_world = (rotation_matrix @ corners_local.T).T + translation

        return corners_world

    def camera_info_callback(self, msg: CameraInfo):
        if msg is None:
            self.get_logger().warn("Camera info message not received")
            return

        # Extract the camera intrinsic matrix K and distortion coefficents
        self.K = np.array(msg.k).reshape(3, 3)
        self.dist_coeffs = np.array(msg.d).reshape(-1, 1)

        # get the frame id of the camera
        self.camera_frame_id = msg.header.frame_id
        self.get_logger().info(f"the camera frame is: {self.camera_frame_id}")

        # destroy the camera info subscriber after receiving the first message
        self.destroy_subscription(self.camera_info_sub)

    def detections_callback(self, msg: AprilTagDetectionArray):
        if len(msg.detections) == 0:
            return

        # emptying the old data
        self.detected_img_corners = []
        self.detected_global_corners = []
        self.n_detected_tags = 0

        for detection in msg.detections:
            self.n_detected_tags += 1
            tag_id = detection.id

            # check whether the detected tag id is in the global location data
            if tag_id not in self.tag_global_corners:
                self.get_logger().warn(f"Tag ID {tag_id} not found in global location file.")
                continue

            # get image corners of the detected april tag
            img_corners = [(corner.x, corner.y) for corner in detection.corners]

            # append the img corners and the global corners
            self.detected_img_corners.append(img_corners)
            self.detected_global_corners.append(self.tag_global_corners[tag_id])

        if len(self.detected_img_corners) == 1:
            self.detected_img_corners = np.array(self.detected_img_corners[0]).reshape(4, 2)
            self.detected_global_corners = np.array(self.detected_global_corners[0]).reshape(4, 3)
        else:
            self.detected_img_corners = np.vstack(self.detected_img_corners)
            self.detected_global_corners = np.vstack(self.detected_global_corners)

    def timer_callback(self) -> None:
        if self.detected_global_corners is None or self.tag_global_corners is None or self.K is None:
            return

        # check for atleast 2 detected tags at once
        if self.n_detected_tags < 2:
            self.get_logger().info("Not enough tag points for stable pose (need at least 2 detected tags)")
            return

        # find the optimised pose
        try:
            # success, rvec, tvec = cv2.solvePnP(
            #     objectPoints=self.detected_global_corners,
            #     imagePoints=self.detected_img_corners,
            #     cameraMatrix=self.K,
            #     distCoeffs=self.dist_coeffs,
            #     flags=cv2.SOLVEPNP_ITERATIVE,
            # )
            success, rvec, tvec, inliers = cv2.solvePnPRansac(
                objectPoints=self.detected_global_corners,
                imagePoints=self.detected_img_corners,
                cameraMatrix=self.K,
                distCoeffs=self.dist_coeffs,
                iterationsCount=1000,
                reprojectionError=3.0,
                confidence=0.99,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )

            if not success:
                self.get_logger().info("PnP failed to find a valid pose...")
                return

            # convert rotation vector to rotation matrix
            R_world_to_cam, _ = cv2.Rodrigues(rvec)

            # Invert the transform to get camera-to-world
            R_cam_to_world = R_world_to_cam.T
            t_cam_to_world = -R_world_to_cam.T @ tvec

            # convert to quaternion
            rot = Rotation.from_matrix(R_cam_to_world)
            quat = rot.as_quat()

            # Print the pose
            self.get_logger().info(f"Camera position (x, y, z): {t_cam_to_world.ravel()}")
            self.get_logger().info(f"Camera orientation (quaternion): {quat}")

        except Exception as e:
            self.get_logger().error(f"PnP failed: {str(e)}")


def main(args=None) -> None:
    rclpy.init(args=args)

    try:
        node = OptimizePose()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("Node stopped by user 🛑")
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
