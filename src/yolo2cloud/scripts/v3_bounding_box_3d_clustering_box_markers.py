#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import numpy as np
import cv2
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2DArray, BoundingBox3DArray
from sklearn.cluster import DBSCAN

from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA

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
        self.timer = self.create_timer(0.1, self.timer_callback)

        # publishers
        self.bbox_3d_pub = self.create_publisher(BoundingBox3DArray, "detection_bboxes_3d", 10)
        self.marker_pub = self.create_publisher(MarkerArray, "bounding_box_markers", 10)
        

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

    def cluster_foreground_points_dbscan(self, depth_roi, x1, y1, x2, y2):
        skip_step = 10
        depth_roi_skipped = depth_roi[::skip_step, ::skip_step]
        u_coords, v_coords = np.meshgrid(np.arange(x1, x2, skip_step), np.arange(y1, y2, skip_step))
        
        valid_mask = depth_roi_skipped > 0
        
        if np.sum(valid_mask) < 20:
            self.get_logger().warn("Not enough valid pixels in the depth ROI for clustering")
            return None
        
        # get 3D corrdinates of the valid pixels
        Z = depth_roi_skipped[valid_mask] / 1000.0  # convert from mm to meters
        u_coords = u_coords[valid_mask]
        v_coords = v_coords[valid_mask]
        
        X = (u_coords - self.K[0, 2]) * Z / self.K[0, 0]
        Y = (v_coords - self.K[1, 2]) * Z / self.K[1, 1]
        
        # # create point clouds for clustering
        point_cloud = np.column_stack((X, Y, Z))        #shape (N, 3)
        
        # # apply DBSCAN clustering
        dbscan = DBSCAN(eps=0.1, min_samples=5)  
        labels = dbscan.fit_predict(point_cloud)
        
        # find the largest cluster
        unique_labels, counts = np.unique(labels[labels != -1], return_counts=True)
        if len(unique_labels) == 0:
            self.get_logger().warn("No valid clusters found in the depth ROI")
            return None
        
        largest_cluster_label = unique_labels[np.argmax(counts)]
        foreground_mask = labels == largest_cluster_label
        
        foreground_points = point_cloud[foreground_mask]
        
        # self.get_logger().info(f"depth_roi: {depth_roi.shape}")
        # self.get_logger().info(f"depth_roi_skipped: {depth_roi_skipped.shape}")
        # self.get_logger().info(f"Number of valid pixels in the depth ROI: {np.sum(valid_mask)}")
        # self.get_logger().info(f"Number of foreground points in the largest cluster: {foreground_points.shape[0]}")
        
        return foreground_points
        

    def create_bounding_box_marker(self, bbox_coords, marker_id, class_id, frame_id):
        x_min, y_min, z_min, x_max, y_max, z_max = bbox_coords
        
        # create marker
        marker = Marker()
        marker.header.frame_id = frame_id
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.id = marker_id
        marker.type = Marker.LINE_LIST
        marker.action = Marker.ADD
        
        # set marker scale
        marker.scale.x = 0.05  # line width
        
        # set marker color
        color = ColorRGBA()
        color.r = 1.0
        color.g = 0.0
        color.b = 0.0
        color.a = 1.0
        marker.color = color
        
        # Define 8 corner points of the bounding box
        corners = [
            Point(x=x_min, y=y_min, z=z_min),  # 0: bottom-front-left
            Point(x=x_max, y=y_min, z=z_min),  # 1: bottom-front-right
            Point(x=x_max, y=y_max, z=z_min),  # 2: bottom-back-right
            Point(x=x_min, y=y_max, z=z_min),  # 3: bottom-back-left
            Point(x=x_min, y=y_min, z=z_max),  # 4: top-front-left
            Point(x=x_max, y=y_min, z=z_max),  # 5: top-front-right
            Point(x=x_max, y=y_max, z=z_max),  # 6: top-back-right
            Point(x=x_min, y=y_max, z=z_max),  # 7: top-back-left
        ]
        
        # Define lines connecting the corners (12 edges of a cube)
        lines = [
            # Bottom face edges
            (0, 1), (1, 2), (2, 3), (3, 0),
            # Top face edges  
            (4, 5), (5, 6), (6, 7), (7, 4),
            # Vertical edges
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]
        
        # Add points for each line (LINE_LIST requires pairs of points)
        marker.points = []
        for start_idx, end_idx in lines:
            marker.points.append(corners[start_idx])
            marker.points.append(corners[end_idx])
            
         # Set lifetime (0 means forever until replaced)
        marker.lifetime = rclpy.duration.Duration(seconds=0.5).to_msg()
        
        return marker
        

    def timer_callback(self):
        
        if self.depth_image is None:
            self.get_logger().warn("Depth image not received yet")
            return

        if self.K is None:
            self.get_logger().warn("Camera intrinsic matrix K not received yet")
            return

        if not self.detections_msg:
            return
        
         # Create marker array for all bounding boxes
        marker_array = MarkerArray()

        for idx, detection in enumerate(self.detections_msg.detections):
            bbox = detection.bbox
            # -----------------------------------   Extract the bounding box coordinates and details
            # extract the class id and score
            class_id = detection.results[0].hypothesis.class_id
            score = detection.results[0].hypothesis.score

            # extract the ROI from the depth image
            center_x, center_y, x1, y1, x2, y2 = self.get_depth_roi_coords(bbox)
            depth_roi = self.depth_image[y1:y2, x1:x2]

            # apply clustering
            foreground_points = self.cluster_foreground_points_dbscan(depth_roi, x1, y1, x2, y2)
            
            if foreground_points is None or foreground_points.shape[0] < 10:
                self.get_logger().warn("No valid foreground points found in the depth ROI")
                continue
            
            # calculate the 3d bounding box from clustered points
            x_min, x_max = np.min(foreground_points[:, 0]), np.max(foreground_points[:, 0])
            y_min, y_max = np.min(foreground_points[:, 1]), np.max(foreground_points[:, 1])
            z_min, z_max = np.min(foreground_points[:, 2]), np.max(foreground_points[:, 2])
            
            self.get_logger().info(f"({x_min}, {y_min}, {z_min})      ({x_max}, {y_max}, {z_max})")
            
            # CREATE AND ADD MARKER
            bbox_coords = (x_min, y_min, z_min, x_max, y_max, z_max)
            marker = self.create_bounding_box_marker(
                bbox_coords=bbox_coords,
                marker_id=idx,
                class_id=str(class_id),
                frame_id="oak"  # Use your camera frame here
            )
            
            marker_array.markers.append(marker)
            
        # publish the marker array
        if marker_array.markers:
            self.get_logger().info(f"Publishing {len(marker_array.markers)} bounding box markers")
            self.marker_pub.publish(marker_array)



def main(args=None):
    rclpy.init(args=args)
    node = BoundingBox3D()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
