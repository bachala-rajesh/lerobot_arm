#!/usr/bin/env python3

"""
YOLO object detection ROS2 Node for Real-Time 2D Object Detection
--------------------------------------------------

This ROS2 node performs real-time 2D object detection on RGB images using
a YOLO object detection model (via the `ultralytics` library). It publishes detected
objects as `vision_msgs/Detection2DArray` messages.

Main Features:
--------------
- Subscribes to:
    - /rgb_camera/image_raw (sensor_msgs/Image) — raw RGB image stream

- Publishes:
    - /detections_2d (vision_msgs/Detection2DArray) — 2D detections with class and confidence

- Parameters:
    - camera_topic        : Topic to subscribe for RGB image (default: "/rgb_camera/image_raw")
    - model_name          : Name of YOLOv8 model file (e.g., "yolov8n.pt")
    - view_detections     : Whether to display results in an OpenCV window (default: True)
    - detect_classes      : List of class names to detect (e.g., ["person", "car"])

Detection Pipeline:
-------------------
1. Converts ROS image to OpenCV format using CvBridge
2. Runs YOLOv8 model inference on the image
3. Filters results based on user-specified classes
4. Converts detections into ROS Detection2D messages:
    - Normalized bounding boxes are scaled to image size
    - Class name and confidence are added
5. Publishes all detections as a Detection2DArray message
6. Optionally displays the annotated image

To Do:
------
- make it component-based for better modularity
"""



import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
import torch
from ament_index_python.packages import get_package_share_directory
from pathlib import Path
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose


class YoloObjectDetection(Node):
    def __init__(self):
        super().__init__("yolo_object_detection_node")
        # parameter variables
        self.camera_topic = "/rgb_camera/image_raw"
        self.model_name = "yolov8n.pt"
        self.view_detections = True
        self.detect_class_names = ["person", "car"]

        # Declare parameters
        self.declare_parameter("camera_topic", self.camera_topic)
        self.declare_parameter("model_name", self.model_name)
        self.declare_parameter("view_detections", self.view_detections)
        self.declare_parameter("detect_classes", self.detect_class_names)  # list of class names

        # get the params
        self.get_params()
        
        # image subscriber
        self.image_sub = self.create_subscription(Image, self.camera_topic, self.image_callback, 10)
        # object detection publisher
        self.obj_det_pub = self.create_publisher(Detection2DArray, "detections_2d", 10)
        # cvbridge object
        self.cv_bridge = CvBridge()

        # get model path and define object detection model
        self.model_path = self.get_model_path(model_name=self.model_name)
        self.model = YOLO(self.model_path)

        #mapping the class names to the ids
        self.detect_class_ids = []
        self.map_class_names_to_ids()
        
        # yolo model arguments
        self.yolo_args = {
            "device": "cuda:0",
            "half": True,
            "conf": 0.75,
            "verbose": False,
            "classes": self.detect_class_ids  
        }
        
        # image size related variables
        self.img_height = 0
        self.img_width = 0
        self.has_img_size = False

        # logging
        self.get_logger().info(f"YOLO object detector node started with model {self.model_name}...")

    def get_params(self):
        self.camera_topic = self.get_parameter("camera_topic").get_parameter_value().string_value
        self.model_name = self.get_parameter("model_name").get_parameter_value().string_value
        self.view_detections = self.get_parameter("view_detections").get_parameter_value().bool_value
        self.detect_class_names = self.get_parameter("detect_classes").get_parameter_value().string_array_value

    def get_model_path(self, model_name):
        p = Path(get_package_share_directory("deep_learning_models"))
        model_path = p / "models" / "converted_models" / "yolo" / "object_detection" / model_name

        if model_path.exists():
            self.get_logger().info(f"model path retrived successfully: {model_path}")
            return str(model_path)
        else:
            self.get_logger().error(
                f"model does not exists at this path... please check the model at the destined path...{model_path}"
            )
            self.destroy_node()


    def map_class_names_to_ids(self):
        self.class_to_id = {name: i for i, name in self.model.names.items()}
        
        for name in self.detect_class_names:
            if name in self.class_to_id:
                self.detect_class_ids.append(self.class_to_id[name])
            else:
                self.get_logger().warn(f"Class name -{name} not found in the model.. Ignoring the class...!")
                
        # logging the found classes
        self.get_logger().info(f"Will detect classes with IDs: {self.detect_class_ids}")
            
    
          
    def fill_detection_msg(self, class_id, conf_score, norm_coords):
        # fill the detection message
        det_msg =  Detection2D()
        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis.class_id = str(self.model.names[class_id])
        hypothesis.hypothesis.score = conf_score
        
        det_msg.results.append(hypothesis)
        det_msg.bbox.center.position.x = float(norm_coords[0] * self.img_width)
        det_msg.bbox.center.position.y = float(norm_coords[1] * self.img_height)
        det_msg.bbox.size_x = float(norm_coords[2] * self.img_width)
        det_msg.bbox.size_y = float(norm_coords[3] * self.img_height)
        
        return det_msg
        
        

    def image_callback(self, msg):
        if msg is None:
            self.get_logger().warn("Image message not received")
            return
        try:
            # decode the image message
            frame = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

            if frame is None or frame.size == 0:
                self.get_logger().warn("Empty frame after conversion!")
                return
            
            if not self.has_img_size:
                self.img_height, self.img_width = frame.shape[:2]
                self.has_img_size = True


            # get results
            results = self.model(frame, **self.yolo_args)[0]
            
            # msg for detection
            det_array_msg = Detection2DArray()
            det_array_msg.header = msg.header
            
            # loop through the detected boxes 
            for box in results.boxes:
                class_id = int(box.cls.item())
                conf_score = float(box.conf.item())
                norm_coords = box.xywhn[0]

                # fill the Detection2D message
                det_msg = self.fill_detection_msg(class_id, conf_score, norm_coords)
                det_array_msg.detections.append(det_msg)
            
                
            # publish the detection array
            self.obj_det_pub.publish(det_array_msg)
               

            # display the result
            if self.view_detections:
                annotated = results.plot()
                self.get_logger().info("visualising plots")
                
                cv2.imshow("object_detection", annotated)
                cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f"Error during YOLO inference: {e}")
  

def main(args=None):
    rclpy.init(args=args)
    node = YoloObjectDetection()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()



