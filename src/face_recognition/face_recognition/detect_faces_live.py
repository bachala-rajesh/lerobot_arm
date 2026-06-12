#!/usr/bin/env python3


"""
Steps Overview: Face Detection ROS2 Service Node

Initialize:
   - ROS2 image subscriber for camera frames.
   - ROS2 service server for face detection requests.
   - Deep learning models for face detection and embedding.
   - CvBridge for image conversion.
Load data from JSON database:
    - Utility function to load face embeddings from a JSON database.
In image_callback:
   - Convert incoming ROS2 image messages to OpenCV images.
   - Store the latest image for processing.
In detect_faces_callback:
   - Check if an image is available.
   - Detect faces in the latest image using the detection model.
   - For each detected face:
     - Extract face region and align it.
     - Compute face embedding.
     - Prepare the response:
       - Set detection flags and counters.
       - Append recognized names, confidence scores, and bounding boxes (as BoundingBox messages).
"""






import cv2
import numpy as np
from facenet_pytorch import InceptionResnetV1
import torch
import json
import rclpy
from rclpy.node import Node
from ament_index_python import get_package_share_directory
from pathlib import Path
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import sys
from utils_detect_faces import get_embedding, is_file_exists, align_face, expand_bbox
from vbot_interfaces.srv import FaceDetectServiceInterface
from vbot_interfaces.msg import BoundingBox


np.set_printoptions(precision=4, suppress=True)


class DetectFacesServer(Node):
    def __init__(self):
        super().__init__("detect_faces_server_node")

        # subscriber
        self.image_sub = self.create_subscription(Image, "/oak/rgb/image_raw", self.image_callback, 10)

        # service server
        self.service_server = self.create_service(FaceDetectServiceInterface, "detect_faces_service", self.detect_faces_callback)

        self.yunet_face_detector_model = None
        self.facenet_embedding_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # variables
        self.images = []
        self.image = None

        # cvbridge object
        self.cv_bridge = CvBridge()

        # intialize the models
        self.initialize_models()
        
        # logging
        self.get_logger().info("The detect_faces_server_node is ready.....")
        

    def initialize_models(self):
        dl_package = Path(get_package_share_directory("deep_learning_models"))
        yunet_model_path = (
            dl_package / "models" / "converted_models" / "yunet" / "face_detection_yunet_2023mar_int8.onnx"
        )
        facenet_model_path = dl_package / "models" / "raw_models" / "facenet" / "facenet_pretrained_vggface2.pt"

        ################ yunet model
        if is_file_exists(yunet_model_path):  # check for whether file exists or not
            # load yunet face detector
            try:
                self.yunet_face_detector_model = cv2.FaceDetectorYN.create(
                    str(yunet_model_path), "", (320, 320), score_threshold=0.7
                )
                self.get_logger().info("yunet model loaded successfully")
            except Exception as e:
                self.get_logger().error(f"Error loading yunet face detection model: {e}")
                sys.exit(1)

        ################# facenet model
        if is_file_exists(facenet_model_path):  # check for whether file exists or not
            # load facenet embbedding model
            try:
                # Step 1: Create model on CPU
                self.facenet_embedding_model = InceptionResnetV1(pretrained=None).eval()

                # Step 2: Load weights to CPU
                checkpoint = torch.load(facenet_model_path, map_location="cpu")

                # Step 3: Filter compatible weights (all on CPU)
                model_state = self.facenet_embedding_model.state_dict()
                filtered_checkpoint = {k: v for k, v in checkpoint.items() if k in model_state}

                # Step 4: Load weights to CPU model
                self.facenet_embedding_model.load_state_dict(filtered_checkpoint)

                # Step 5: Single transfer to GPU
                self.facenet_embedding_model = self.facenet_embedding_model.to(self.device)

                self.get_logger().info("the facenet model loaded successfully")
            except Exception as e:
                self.get_logger().error(f"Error loading facenet embedding model: {e}")
                sys.exit(1)

    def image_callback(self, msg):
        if msg is None:
            self.get_logger().warn("Image message not received")
            return

        
        # decode the image message
        self.image = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        
        # viewing the frame for debug
        # cv2.imshow("frame", self.image)
        # cv2.waitKey(1)
        

        
    def detect_faces_callback(self, request, response):
        if self.image is None:
            self.get_logger().warn("Image message not received")
            return response

        height, width = self.image.shape[:2]
        self.yunet_face_detector_model.setInputSize((width, height))
        _, faces = self.yunet_face_detector_model.detect(self.image)

        if faces is not None:
            
            for face in faces:
                x, y, w, h = map(int, face[:4])
                left_eye = tuple(map(int, face[4:6]))
                right_eye = tuple(map(int, face[6:8]))

                # region of interest
                nx, ny, nw, nh = expand_bbox(x, y, w, h, width, height, margin=0.3)
                roi_image = self.image[ny : ny + nh, nx : nx + nw]

                # Adjust eyes to ROI coordinates
                roi_left_eye = (left_eye[0] - nx, left_eye[1] - ny)
                roi_right_eye = (right_eye[0] - nx, right_eye[1] - ny)

    

                # align face
                aligned_face = align_face(roi_image, roi_left_eye, roi_right_eye)
                if aligned_face is None or aligned_face.size == 0:
                    self.get_logger().warn("Warning: aligned face is None or empty, skipping.")
                    continue
                else:
                    cv2.imshow("aligned_face", aligned_face)

                # get embeddings
                embedding = get_embedding( self.facenet_embedding_model, aligned_face, self.device)

                
                
                # response message
                response.face_found = True
                response.num_faces += 1
                response.names.append("raj")                    #for debug
                response.confidence_score.append(1.0)           #for debug
                bbox = BoundingBox()
                bbox.x = float(x)
                bbox.y = float(y)
                bbox.w = float(w)
                bbox.h = float(h)
                response.coordinates.append(bbox)

                # viewing the laigned face for debug
                cv2.imshow("aligned_face", aligned_face)
                cv2.waitKey(1)

        else:
            self.get_logger().info("Face not detected in the image")
            
        return response

    def load_embeddings_from_json(self, path_json_file):
        with open(path_json_file, "r") as f:
            db = json.load(f)

        # For example, get all embeddings and names:
        names = []
        embeddings_db = []
        for entry in db:
            names.append(entry["name"])
            embeddings_db.append(np.array(entry["embedding"]))

        embeddings_db = np.stack(embeddings_db)  # shape: (num_users, 512)
        return names, embeddings_db


def main(args=None):
    rclpy.init(args=args)
    node = DetectFacesServer()
    rclpy.spin(node)
    node.close_all_windows()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
