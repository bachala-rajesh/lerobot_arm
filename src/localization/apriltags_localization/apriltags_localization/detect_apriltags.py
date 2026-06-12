#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from apriltag_msgs.msg import AprilTagDetectionArray
from geometry_msgs.msg import Pose, TransformStamped
from sensor_msgs.msg import CameraInfo, Image
import numpy as np
from cv_bridge import CvBridge
from typing import Optional
from dt_apriltags import Detector
import sys
import cv2
from tf2_ros import TransformBroadcaster
from scipy.spatial.transform import Rotation


class DetectApriltags(Node):
    def __init__(self):
        super().__init__("detect_apriltags_node")

        # declare parameters
        self.declare_parameter("tag_family", "36h11")
        self.declare_parameter("edge_length", 1.0)
        self.declare_parameter("nthreads", 1)
        self.declare_parameter("quad_decimate", 1.0)
        self.declare_parameter("quad_sigma", 0.0)
        self.declare_parameter("refine_edges", 1)
        self.declare_parameter("decode_sharpening", 0.25)

        # Publisher
        # self.publisher = self.create_publisher(Pose, '/pose_apriltags', 10)

        # Subscribers
        self.camera_info_sub = self.create_subscription(CameraInfo, "/camera_info", self.camera_info_callback, 10)
        self.image_sub = self.create_subscription(Image, "/image_rect", self.image_callback, 10)

        # Timer
        timer_period_sec: float = 0.3
        self.timer = self.create_timer(timer_period_sec, self.timer_callback)

        # tf2 broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)

        # global_variables
        self.K = None  # camera intrinsic matrix
        self.camera_params = None
        self.camera_frame_id = "camera_optical_frame"
        self.current_frame = None  # current frame
        self.cv_bridge = CvBridge()
        self.apriltag_detector = None

        # paramter variables
        self.tag_family = None
        self.edge_tag_length = None
        self.nthreads = 1
        self.quad_decimate = 1.0
        self.quad_sigma = 0.0
        self.refine_edges = 1
        self.decode_sharpening = 0.25

        self.flip_z_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, -1]])

        # get the params
        self.get_params()

        # intialize the apriltag detector
        self.init_tag_detector()

        self.get_logger().info("Detect april tgas node initialized and running ✅")

    def get_params(self):
        self.tag_family = self.get_parameter("tag_family").get_parameter_value().string_value
        self.edge_tag_length = self.get_parameter("edge_length").get_parameter_value().double_value
        self.nthreads = self.get_parameter("nthreads").get_parameter_value().integer_value
        self.quad_decimate = self.get_parameter("quad_decimate").get_parameter_value().double_value
        self.quad_sigma = self.get_parameter("quad_sigma").get_parameter_value().double_value
        self.refine_edges = self.get_parameter("refine_edges").get_parameter_value().integer_value
        self.decode_sharpening = self.get_parameter("decode_sharpening").get_parameter_value().double_value

    def init_tag_detector(self):
        if self.tag_family is None:
            self.get_logger().error("could not intialise the april tag detector.. exiting  🛑...")
            sys.exit(1)

        self.apriltag_detector = Detector(
            families=self.tag_family,
            nthreads=self.nthreads,
            quad_decimate=self.quad_decimate,
            quad_sigma=self.quad_sigma,
            refine_edges=self.refine_edges,
            decode_sharpening=self.decode_sharpening,
            debug=0,
        )

        self.get_logger().info(f"apriltag detector of family: {self.tag_family} initialized...")

    def camera_info_callback(self, msg: CameraInfo):
        if msg is None:
            self.get_logger().warn("Camera info message not received")
            return

        # Extract the camera intrinsic matrix K
        self.K = np.array(msg.k).reshape(3, 3)
        # extract the camera_params
        self.camera_params = (self.K[0, 0], self.K[1, 1], self.K[0, 2], self.K[1, 2])

        # get the frame id of the camera
        self.camera_frame_id = msg.header.frame_id
        self.get_logger().info(f"the camera frame is: {self.camera_frame_id}")

        # destroy the camera info subscriber after receiving the first message
        self.destroy_subscription(self.camera_info_sub)

    def image_callback(self, msg: Image):
        if not msg.data or len(msg.data) == 0:
            self.current_frame = None
            self.get_logger().warn("Image data is empty")
            return

        # decode the image message
        self.current_frame = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        # convert to grayscale if not grayscale
        if msg.encoding in ["bgr8", "rgb8"]:
            if msg.encoding == "bgr8":
                self.current_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
            else:
                self.current_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2GRAY)

    def publish_tfs(self, tag_id, R, T, time_stamp):
        t = TransformStamped()
        t.header.stamp = time_stamp
        t.header.frame_id = self.camera_frame_id
        t.child_frame_id = f"tag_{tag_id}"

        # set translation
        t.transform.translation.x = T[0]
        t.transform.translation.y = T[1]
        t.transform.translation.z = T[2]

        # set rotation
        t.transform.rotation.x = R[0]
        t.transform.rotation.y = R[1]
        t.transform.rotation.z = R[2]
        t.transform.rotation.w = R[3]

        # broadcast
        self.tf_broadcaster.sendTransform(t)

        # logging
        self.get_logger().debug(f"the transform is published between {self.camera_frame_id} and tag_{tag_id} ")



    def timer_callback(self) -> None:
        if self.K is None or self.current_frame is None:
            return

        detections = self.apriltag_detector.detect(
            self.current_frame,
            estimate_tag_pose=True,  # True for estimating pose
            camera_params=self.camera_params,
            tag_size=self.edge_tag_length,
        )
        # get current timestamp
        time_stamp = self.get_clock().now().to_msg()
        
        for detection in detections:
            # get rotation, trnaslationmatrix and the tag id
            R = detection.pose_R
            T = detection.pose_t.flatten()
            tag_id = detection.tag_id
            
            # Convert to quaternion
            R_quat = Rotation.from_matrix(R).as_quat()
            
            # Publish corrected transform
            self.publish_tfs(tag_id, R_quat, T, time_stamp)


def main(args=None) -> None:
    rclpy.init(args=args)

    try:
        node = DetectApriltags()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("Node stopped by user 🛑")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
