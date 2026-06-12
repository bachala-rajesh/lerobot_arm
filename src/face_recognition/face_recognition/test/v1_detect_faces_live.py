#!/usr/bin/env python3


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
from utils_detect_faces import get_embedding, is_file_exists, align_face_smooth_angle, expand_bbox

np.set_printoptions(precision=4, suppress=True)


class DetectFaces(Node):
    def __init__(self):
        super().__init__("detect_faces_node")

        # subscriber
        self.image_sub = self.create_subscription(Image, "/oak/rgb/image_raw", self.image_callback, 10)

        # timer
        # self.timer = self.create_timer(0.01, self.timer_callback)

        self.yunet_face_detector_model = None
        self.facenet_embedding_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.smooth_angle = 0

        # cvbridge object
        self.cv_bridge = CvBridge()

        # intialize the models
        self.initialize_models()

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
        frame = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

        height, width = frame.shape[:2]
        self.yunet_face_detector_model.setInputSize((width, height))
        _, faces = self.yunet_face_detector_model.detect(frame)

        if faces is not None:
            for face in faces:
                x, y, w, h = map(int, face[:4])
                left_eye = tuple(map(int, face[4:6]))
                right_eye = tuple(map(int, face[6:8]))

                # region of interest
                nx, ny, nw, nh = expand_bbox(x, y, w, h, width, height, margin=0.3)
                roi_frame = frame[ny : ny + nh, nx : nx + nw]

                # Adjust eyes to ROI coordinates
                roi_left_eye = (left_eye[0] - nx, left_eye[1] - ny)
                roi_right_eye = (right_eye[0] - nx, right_eye[1] - ny)

                # draw markers
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (left_eye[0], left_eye[1]), 5, (255, 0, 0), -1)
                cv2.circle(frame, (right_eye[0], right_eye[1]), 5, (255, 0, 0), -1)

                # align face
                aligned_face, self.smooth_angle = align_face_smooth_angle(roi_frame, roi_left_eye, roi_right_eye, self.smooth_angle)
                if aligned_face is None or aligned_face.size == 0:
                    self.get_logger().warn("Warning: aligned face is None or empty, skipping.")
                    continue
                else:
                    cv2.imshow("aligned_face", aligned_face)

                # get embeddings
                embedding = get_embedding( self.facenet_embedding_model, aligned_face, self.device)

                print(embedding.shape)

            # display the frame
            cv2.imshow("frame", frame)
            cv2.waitKey(1)
        else:
            self.get_logger().info("Face not detected in the frame")

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
    node = DetectFaces()
    rclpy.spin(node)
    node.close_all_windows()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
