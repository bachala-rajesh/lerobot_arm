#!/usr/bin/env python3


"""
This script runs the two ROS 2 nodes: one for YOLO object detection and another for 3D bounding box processing.
This enables to run the two nodes in a single process for better performance and resource management.

ToDo:
add reentrant groups to the nodes to allow for concurrent execution of callbacks.
"""

import rclpy
from rclpy.executors import MultiThreadedExecutor
import cv2

# Import your existing classes here
from yolo_object_detection import YoloObjectDetection
from bounding_box_3d import BoundingBox3D  # Adjust import if needed

def main(args=None):
    rclpy.init(args=args)
    
    
    # Instantiate both nodes
    yolo_node = YoloObjectDetection()
    bbox3d_node = BoundingBox3D()
    
    # Add to a MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(yolo_node)
    executor.add_node(bbox3d_node)
    try:
        executor.spin()
    finally:
        yolo_node.destroy_node()
        bbox3d_node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
