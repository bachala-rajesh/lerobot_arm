#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import numpy as np
import cv2
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2DArray, BoundingBox3DArray
from sklearn.cluster import DBSCAN

class BoundingBox3D(Node):
    def __init__(self):
        super().__init__("bounding_boxes_3d_node")

        # subscribers
        self.depth_sub = self.create_subscription(Image, "/oak/stereo/image_raw", self.depth_image_callback, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, "/oak/rgb/camera_info", self.camera_info_callback, 10
        )
        self.detections_2d_sub = self.create_subscription(
            Detection2DArray, "detections_2d", self.detections_2d_callback, 10
        )

        # timer
        self.timer = self.create_timer(0.5, self.timer_callback)

        # publishers
        self.bbox_3d_pub = self.create_publisher(BoundingBox3DArray, "detection_bboxes_3d", 10)

        # cvbridge object
        self.cv_bridge = CvBridge()

        # variables
        self.K = None
        self.depth_image = None
        self.detections_msg = None
        self.RATIO_PIXEL_THRESHOLD = 0.70  # threshold for valid pixels in the depth ROI

        # logging
        self.get_logger().info(" Nodes for 3d boudning boxes launched...")

    def camera_info_callback(self, msg: CameraInfo):
        if msg is None:
            self.get_logger().warn("Camera info message not received")
            return
        # Extract the camera intrinsic matrix K
        self.K = np.array(msg.k).reshape(3, 3)

        self.get_logger().info(f"Camera intrinsic matrix K: {self.K}")

        # destroy the camera info subscriber after receiving the first message
        self.destroy_subscription(self.camera_info_sub)

    def depth_image_callback(self, msg: Image):
        if msg is None:
            self.depth_image = None
            self.get_logger().warn("Depth image message not received")
            return

        # decode the image message
        self.depth_image = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

    def detections_2d_callback(self, msg: Detection2DArray):
        if msg is None or msg.detections is None:
            self.detections_msg = None
            return

        self.detections_msg = msg

    def get_depth_roi_coords(self, bbox):
        # extract the bounding box center and size
        center_x = int(bbox.center.position.x)
        center_y = int(bbox.center.position.y)
        width = int(bbox.size_x)
        height = int(bbox.size_y)

        # calculate the top-left and bottom-right coordinates of the bounding box and check for bounds
        # to ensure they are within the depth image dimensions
        x1 = max(0, center_x - width // 2)
        y1 = max(0, center_y - height // 2)
        x2 = min(self.depth_image.shape[1] - 1, center_x + width // 2)
        y2 = min(self.depth_image.shape[0] - 1, center_y + height // 2)
        return center_x, center_y, x1, y1, x2, y2

    def timer_callback(self):
        if self.depth_image is None:
            self.get_logger().warn("Depth image not received yet")
            return

        if self.K is None:
            self.get_logger().warn("Camera intrinsic matrix K not received yet")
            return

        if not self.detections_msg:
            return

        for detection in self.detections_msg.detections:
            bbox = detection.bbox
            # -----------------------------------   Extract the bounding box coordinates and details
            # extract the class id and score
            class_id = detection.results[0].hypothesis.class_id
            score = detection.results[0].hypothesis.score

            # extract the ROI from the depth image
            center_x, center_y, x1, y1, x2, y2 = self.get_depth_roi_coords(bbox)
            depth_roi = self.depth_image[y1:y2, x1:x2]

            # check if the depth ROI is empty
            if depth_roi.size == 0:
                self.get_logger().warn("Depth ROI is empty, skipping detection")
                continue

            # -----------------------------------  filter depth values and find median depth
            # find valid depth values- those greater than 0
            valid_depths = depth_roi[depth_roi > 0]
            ratio_valid_pixels = valid_depths.size/depth_roi.size
            
            # check if the ratio of valid pixels is below the threshold. This is to avoid cases where the depth ROI is mostly background or invalid pixels
            if ratio_valid_pixels < self.RATIO_PIXEL_THRESHOLD:
                object_depth = np.inf
                continue
                
            # calculate the median depth but to avoid the background dominating the depth, use the 25th percentile
            object_depth = np.percentile(valid_depths, q=25) 

            

            # ----------------------------------   Project 2D center to 3D point
            # deprojection
            center_Z = object_depth / 1000.0        # convert from mm to meters
            center_X = (center_x - self.K[0, 2]) * Z / self.K[0, 0]
            center_Y = (center_y - self.K[1, 2]) * Z / self.K[1, 1]

           




def main(args=None):
    rclpy.init(args=args)
    node = BoundingBox3D()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
