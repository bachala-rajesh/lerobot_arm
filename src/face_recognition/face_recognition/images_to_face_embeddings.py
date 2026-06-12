#!/usr/bin/env python3

"""
Face Images to Embeddings Pipeline - Summary of Steps

1. Ask the user for their details (name, gender, age, email) using console input.
2. Load all images from a specified directory.
3. For each image:
    - Detect the face and facial landmarks (eyes) using Yunet.
    - Expand and crop the face region for better alignment.
    - Align the face so the eyes are horizontal (optional but recommended).
    - Pass the aligned face through FaceNet to generate a 512-d embedding.
4. Collect all embeddings for the user and compute the mean embedding.
5. Prepare a user data dictionary with user info and mean embedding.
6. Save or update this user data in a JSON file:
    - If the user already exists (by name), update their info and embedding.
    - Otherwise, add as a new user.
7. The JSON file acts as your face embeddings database for future recognition.

T
"""

from pathlib import Path
import cv2
import math
from facenet_pytorch import InceptionResnetV1
import numpy as np
import json
import torch
from typing import Tuple
from ament_index_python import get_package_share_directory
import os
import sys
from utils_detect_faces import get_embedding, is_file_exists, align_face, expand_bbox
from typing import List


class ImageToFaceEmbeddings:
    def __init__(self, yunet_model_path, facenet_model_path):
        self.yunet_model_path = yunet_model_path
        self.facenet_model_path = facenet_model_path

        # models
        self.yunet_face_detector_model = None
        self.facenet_embedding_model = None

        # device cpu/gpu
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # load models
        self.get_models_loaded(yunet_model_path, facenet_model_path)

    def get_models_loaded(self, yunet_model_path, facenet_model_path):
        ################ yunet model
        if is_file_exists(yunet_model_path):  # check for whether file exists or not
            # load yunet face detector
            try:
                self.yunet_face_detector_model = cv2.FaceDetectorYN.create(
                    str(yunet_model_path), "", (320, 320), score_threshold=0.7
                )
                print("yunet model loaded successfully")
            except Exception as e:
                print(f"Error loading yunet face detection model: {e}")
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

                print("the facenet model loaded successfully")
            except Exception as e:
                print(f"Error loading facenet embedding model: {e}")
                sys.exit(1)

    def process_images_to_embeddings(self, imgs_folder_path, SHOW_DEBUG_FACE=False):
        """
        Processes a list of image file paths to generate a mean face embedding.

        Args:
            imgs_path (list): List of image file paths to process.

        Return:
            face embeddings in the form of np.ndarray
        """
        # embeddings
        embeddings = []

        # getting all the images path
        img_extensions = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
        imgs_path = []
        for ext in img_extensions:
            imgs_path.extend(imgs_folder_path.glob(ext))

        # Process each image in the directory
        for img_path in imgs_path:
            img = cv2.imread(img_path)

            if img is not None:
                # Set face detector input size
                height, width = img.shape[:2]
                self.yunet_face_detector_model.setInputSize((width, height))

                # detect the faces in the frame
                _, faces = self.yunet_face_detector_model.detect(img)

                if faces is not None:
                    for face in faces:
                        # get the bounding box for face
                        x, y, w, h = map(int, face[:4])
                        # eye coordinates
                        left_eye = tuple(map(int, face[4:6]))
                        right_eye = tuple(map(int, face[6:8]))

                        # expand the bounding box for proper capture of the face
                        nx, ny, nw, nh = expand_bbox(x, y, w, h, width, height, margin=0.2)

                        # region of interest
                        roi_frame = img[ny : ny + nh, nx : nx + nw]

                        # Adjust eyes to ROI coordinates
                        roi_left_eye = (left_eye[0] - nx, left_eye[1] - ny)
                        roi_right_eye = (right_eye[0] - nx, right_eye[1] - ny)

                        # get the aligned face
                        aligned_face = align_face(roi_frame, roi_left_eye, roi_right_eye)

                        #  Optionally show the aligned face (for debugging)
                        if SHOW_DEBUG_FACE:
                            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.circle(img, (left_eye[0], left_eye[1]), 5, (255, 0, 0), -1)
                            cv2.circle(img, (right_eye[0], right_eye[1]), 5, (255, 0, 0), -1)
                            cv2.imshow("aligned_face", aligned_face)
                            cv2.waitKey(0)

                        # get embeddings for the laigned face
                        embs = get_embedding(self.facenet_embedding_model, aligned_face, self.device)
                        # append to the embeddings
                        embeddings.append(embs)
                else:
                    print("unable to detect faces... failed")
            else:
                print("failed to read the image")
        cv2.destroyAllWindows()

        # convert embedding list to numpy array
        if embeddings:
            embeddings = np.stack(embeddings)

            # taking the mean of all the embeddings
            mean_embedding = np.mean(embeddings, axis=0)
            print("Images converted to embeddings successfully...")

            return mean_embedding
        else:
            return None


def check_folders_exists(parent_folder_path, imgs_folder_name):
    imgs_folder_path = parent_folder_path / imgs_folder_name
    if not imgs_folder_path.exists():
        print(f"Error: The folder {imgs_folder_name} does not exists at this path {imgs_folder_path.parent}.")
        return False

    # if the folder exists, then check for number of files
    num_images = len(list(imgs_folder_path.glob("*.jpg")))
    if num_images == 0:
        print(f"Error: The folder {imgs_folder_name} does not contain any images.")
        return False
    else:
        print(f"Number of images in {imgs_folder_name} : {num_images}")
        return True


def get_user_details(imgs_parent_folder_path) -> Tuple[str, str, int, str, str]:
    """
    Collect user details from console input.
    Returns:
        Tuple containing (name, gender, age, email, folder_name)
    Raises:
        ValueError: If input is invalid.
    """
    gender_dict = {1: "female", 2: "male", 3: "non-binary", 4: "Don't want to disclose"}
    try:
        # name input
        name: str = input("Please enter your name: ").strip()

        # gender input
        gender_input: int = int(input("Gender (1: female, 2: male, 3: non-binary, 4: Don't want to disclose): "))
        if gender_input not in gender_dict:
            raise ValueError("Invalid gender selection.")
        gender: str = gender_dict[gender_input]

        # age input
        age: int = int(input("Enter your age: "))
        if age <= 0:
            raise ValueError("Age must be a positive number.")

        # email input
        email: str = input("Enter your email ID: ").strip()

        # folder name imput
        while True:
            imgs_folder_name: str = input("Enter the folder name that contains images: ").strip()
            # check whether the folder exists or not
            if check_folders_exists(imgs_parent_folder_path, imgs_folder_name):
                break
            else:
                print("enter a valid folder name in which images are present.")
                continue

        return name, gender, age, email, imgs_folder_name

    except ValueError as e:
        print(f" Input error: {e}")
        raise


def save_to_json(user_data: dict, path_json_file: str):
    """This function saves the user data to json format in a specified file

    Args:
        user_data : the user data
        path_json_file: JSON file path
    """
    try:
        with open(path_json_file, "r") as f:
            db = json.load(f)
    except FileNotFoundError:
        db = []  # File does not exist, start with empty list

    # check if user already exists,update or append
    for i, entry in enumerate(db):
        if entry["name"] == user_data["name"]:
            db[i] = user_data
            break
    else:
        db.append(user_data)

    with open(path_json_file, "w") as f:
        json.dump(db, f, indent=2)

    # print the success message
    print(f"successfully written the user data to the file: {path_json_file}")
    print(f"Saved {len(db)} users in database: {path_json_file}")


def main():
    # get workspace path from environment variable
    env_var = Path(os.environ.get("ISAAC_ROS_WS", "/workspaces/isaac_ros-dev"))

    # set paths
    dl_package = Path(get_package_share_directory("deep_learning_models"))
    yunet_model_path = dl_package / "models" / "converted_models" / "yunet" / "face_detection_yunet_2023mar_int8.onnx"
    facenet_model_path = dl_package / "models" / "raw_models" / "facenet" / "facenet_pretrained_vggface2.pt"
    save_json_folder_path = env_var / "src" / "face_recognition" / "processed_data"
    imgs_parent_folder_path = env_var / "src" / "face_recognition" / "data"

    # ImageToFaceEmbeddings obj
    img_to_embeddings = ImageToFaceEmbeddings(yunet_model_path, facenet_model_path)

    # Collect user details
    name, gender, age, email, imgs_folder_name = get_user_details(imgs_parent_folder_path)

    # get image folder path
    imgs_folder_path = imgs_parent_folder_path / str(imgs_folder_name)
    mean_embedding = img_to_embeddings.process_images_to_embeddings(imgs_folder_path, SHOW_DEBUG_FACE=True)

    if mean_embedding is None:
        print("No embeddings were generated. Exiting.")
        sys.exit(1)

    # writing data to json
    try:
        user_data = {"name": name, "gender": gender, "age": age, "email": email, "embedding": mean_embedding.tolist()}

        # save the user_data to the file
        path_json_file = save_json_folder_path / "faces_embeddings_data.json"
        save_to_json(user_data, path_json_file)

    except Exception as e:
        print(f"failed....error while saving the user data.... {e}")


if __name__ == "__main__":
    main()
