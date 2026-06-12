#!/usr/bin/env python3

############ Note: the onnx model is not working in the case of segmentation, the pt model is working well for segmentation. use lighter model for segmentation.


"""
================================================================================
ROS2 YOLO Segmentation to 3D Point Cloud Converter
================================================================================

PURPOSE:
    Real-time object segmentation using YOLO segmentation and conversion to 3D point clouds.

ROS2 INTERFACE:
    SUBSCRIPTIONS:
        • /image         - RGB camera feed (sensor_msgs/Image)
        • /depth_image   - Depth camera feed (sensor_msgs/Image)
        • /camera_info   - Camera calibration (sensor_msgs/CameraInfo)

    PUBLICATIONS:
        • detection_point_clouds - 3D points (sensor_msgs/PointCloud2)


PERFORMANCE OPTIMIZATIONS:
    ✓ Skip-pixel sampling (configurable via skip_pixels parameter)
    • Pre-computed meshgrid coordinates (5-10x faster)

PARAMETERS:
    • model_name: YOLO model file (default: yolov11n-seg.pt)
    • detect_classes: Object classes to detect (default: ["person", "car"])
    • frame_id: TF frame for point clouds (default: "oak")
    • view_detections_debug: Enable CV2 visualization (default: False)

NOTES:
    • ONNX models not working for segmentation - use .pt models only
    • Lighter models recommended for real-time performance
    • Point clouds published in camera optical frame (+Z forward)
    • Depth values converted from mm to meters automatically

# TODO: add filter to the mask to remove the noise

================================================================================
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo, PointCloud2
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
import torch
from ament_index_python.packages import get_package_share_directory
from pathlib import Path
import numpy as np
import sensor_msgs_py.point_cloud2 as pc2
from std_msgs.msg import Header


class YoloSeg2Cloud(Node):
    def __init__(self):
        super().__init__("yolo_seg2cloud_node")
        # parameter variables
        self.model_name = "yolov11n-seg.pt"
        self.view_detections_debug = False
        self.detect_class_names = ["person", "car"]
        self.use_raw_model = True
        self.frame_id = "oak"
        self.skip_pixels = 15
        

        # Declare parameters
        self.declare_parameter("model_name", self.model_name)
        self.declare_parameter("view_detections_debug", self.view_detections_debug)
        self.declare_parameter("detect_classes", self.detect_class_names)  # list of class names
        self.declare_parameter("use_raw_model", self.use_raw_model)  # list of class names
        self.declare_parameter("frame_id", self.frame_id)  # frame_id for point cloud message
        self.declare_parameter("skip_pixels", self.skip_pixels)  # skip_pixels for less computations

        # get the params
        self.get_params()

        # image subscriber
        self.image_sub = self.create_subscription(Image, "/image", self.image_callback, 10)

        # depth image subscriber
        self.depth_image_sub = self.create_subscription(Image, "/depth_image", self.depth_image_callback, 10)

        # camera info subscriber
        self.camera_info_sub = self.create_subscription(CameraInfo, "/camera_info", self.camera_info_callback, 10)

        # point cloud publisher
        self.point_cloud_pub = self.create_publisher(PointCloud2, "detection_point_clouds", 10)

        # timer
        self.timer = self.create_timer(0.1, self.timer_callback)

        # cvbridge object
        self.cv_bridge = CvBridge()

        # get model path and define object segmentation model
        self.model_path = self.get_model_path(model_name=self.model_name)
        self.model = YOLO(self.model_path)

        # mapping the class names to the ids
        self.detect_class_ids = []
        self.map_class_names_to_ids()

        # yolo model arguments
        self.yolo_args = {
            "device": "cuda:0",
            "half": True,
            "conf": 0.75,
            "verbose": False,
            "classes": self.detect_class_ids,
            "retina_masks": True,
            "show_labels": True,
        }

        # variables
        self.K = None
        self.coords_initialized = False
        self.u_coords, self.v_coords = None, None

        # image size related variables
        self.frame = None
        self.img_height = 0
        self.img_width = 0
        self.has_img_size = False

        # depth image related varibles
        self.depth_frame = None

        # logging
        self.get_logger().info(f"YOLO object detector node started with model {self.model_name}...")

    def get_params(self):
        self.model_name = self.get_parameter("model_name").get_parameter_value().string_value
        self.view_detections_debug = self.get_parameter("view_detections_debug").get_parameter_value().bool_value
        self.detect_class_names = self.get_parameter("detect_classes").get_parameter_value().string_array_value
        self.use_raw_model = self.get_parameter("use_raw_model").get_parameter_value().bool_value
        self.frame_id = self.get_parameter("frame_id").get_parameter_value().string_value
        self.skip_pixels = self.get_parameter("skip_pixels").get_parameter_value().integer_value

    def get_model_path(self, model_name):
        p = Path(get_package_share_directory("deep_learning_models"))

        if self.use_raw_model:
            model_path = p / "models" / "raw_models" / "yolo" / "segmentation" / model_name
        else:
            model_path = p / "models" / "converted_models" / "yolo" / "segmentation" / model_name

        if model_path.exists():
            self.get_logger().info(f"model path retrived successfully: {model_path}")
            return str(model_path)
        else:
            self.get_logger().error(
                f"model does not exists at this path... please check the model at the destined path...{model_path}"
            )
            self.destroy_node()

    def initialize_coords(self):
        """Initialize coordinate grids once when we know image size"""
        self.u_coords, self.v_coords = np.meshgrid(
            np.arange(0, self.img_width, self.skip_pixels), np.arange(0, self.img_height, self.skip_pixels)
        )
        self.coords_initialized = True
        self.get_logger().info(f"Coordinates initialized for {self.img_width}x{self.img_height}")

    def map_class_names_to_ids(self):
        self.class_to_id = {name: i for i, name in self.model.names.items()}

        for name in self.detect_class_names:
            if name in self.class_to_id:
                self.detect_class_ids.append(self.class_to_id[name])
            else:
                self.get_logger().warn(f"Class name -{name} not found in the model.. Ignoring the class...!")

        # logging the found classes
        self.get_logger().info(f"Will detect classes with IDs: {self.detect_class_ids}")

    def image_callback(self, msg):
        if msg is None:
            self.frame = None
            self.get_logger().warn("Image message not received")
            return
        try:
            # decode the image message
            self.frame = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

            if self.frame is None or self.frame.size == 0:
                self.get_logger().warn("Empty frame after conversion!")
                return

            # resize the frame
            # self.frame = cv2.resize(self.frame, (320, 320), 0, 0)

            if not self.has_img_size:
                self.img_height, self.img_width = self.frame.shape[:2]
                self.has_img_size = True
                self.initialize_coords()
        except Exception as e:
            self.get_logger().error(f"Error during image frame conversion: {e}")

    def depth_image_callback(self, msg):
        if msg is None:
            self.depth_frame = None
            self.get_logger().warn("Depth image message not received")
            return

        # decode the image message
        try:
            self.depth_frame = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

            # resize the depth frame
            # self.depth_frame = cv2.resize(self.depth_frame, (320, 320), 0, 0)

        except Exception as e:
            self.get_logger().error(f"Error during depth frame conversion: {e}")

    def camera_info_callback(self, msg: CameraInfo):
        if msg is None:
            self.get_logger().warn("Camera info message not received")
            return
        # Extract the camera intrinsic matrix K
        self.K = np.array(msg.k).reshape(3, 3)

        self.get_logger().info(f"Camera intrinsic matrix K: {self.K}")

        # destroy the camera info subscriber after receiving the first message
        self.destroy_subscription(self.camera_info_sub)

    def extract_pointclouds(self, mask):
        masked_depth = self.depth_frame.copy()
        masked_depth[mask] = 0

        u_coords_local = self.u_coords.copy()
        v_coords_local = self.v_coords.copy()

        # get depth values
        depth_values = masked_depth[v_coords_local, u_coords_local]

        # create valid mask
        valid_mask = depth_values > 0

        # keep only valid points
        u_coords_local = u_coords_local[valid_mask]
        v_coords_local = v_coords_local[valid_mask]
        Z = depth_values[valid_mask] / 1000.0  # convert from mm to meters

        X = (u_coords_local - self.K[0, 2]) * Z / self.K[0, 0]
        Y = (v_coords_local - self.K[1, 2]) * Z / self.K[1, 1]

        # # create point clouds for clustering
        point_cloud = np.column_stack((X, Y, Z))  # shape (N, 3)

        return point_cloud

    def create_point_cloud_msg(self, points, frame_id="oak", timestamp=None):
        if points.shape[0] == 0:
            return None

        if timestamp is None:
            timestamp = self.get_clock().now().to_msg()

            # create header
            header = Header()
            header.stamp = timestamp
            header.frame_id = frame_id

            # convert numpy array to list of tuples (x, y , z)
            points_list = [tuple(float(coord) for coord in point) for point in points]

            # create PointCloud2 message using sensor_msgs_py
            point_cloud_msg = pc2.create_cloud_xyz32(header, points_list)

            return point_cloud_msg

    def timer_callback(self):
        # check for empty frame and depth_frame
        if self.frame is None or self.depth_frame is None or self.K is None or not self.coords_initialized:
            return

        try:
            # get results
            results = self.model(self.frame, **self.yolo_args)[0]

            if results.masks is None:
                self.get_logger().warn("No segmentation masks detected...")
                return

            # get the mask
            masks = results.masks.data

            combined_mask = torch.sum(masks, dim=0)  # combine the masks for all detected objects

            # Convert to numpy boolean mask
            mask_numpy = (combined_mask == 0).cpu().numpy()

            # Extract point cloud
            point_cloud = self.extract_pointclouds(mask_numpy)

            # create the point cloud message and publish the point clouds
            if point_cloud is not None:
                point_cloud_msg = self.create_point_cloud_msg(point_cloud, frame_id=self.frame_id)

                # publish the point cloud
                if point_cloud_msg is not None:
                    self.point_cloud_pub.publish(point_cloud_msg)

            # debug - visualization
            if self.view_detections_debug:
                self.frame[mask_numpy] = 0
                cv2.imshow("final_mask", self.frame)
                cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f"Error during YOLO inference: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = YoloSeg2Cloud()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
