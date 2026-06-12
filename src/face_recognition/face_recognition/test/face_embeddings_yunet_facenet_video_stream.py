import cv2
import numpy as np
import math
from facenet_pytorch import InceptionResnetV1
from PIL import Image
import torch
import json
import rclpy
from rclpy import Node


np.set_printoptions(precision=4, suppress=True)



def compute_angle(left_eye, right_eye):
    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]

    angle = math.degrees(math.atan2(dy, dx))
    # convert radians into degrees
    # angle = np.rad2deg(angle)
    print(angle)
    return angle


def align_face(roi_frame, left_eye, right_eye):
    global smooth_angle
    height, width = roi_frame.shape[:2]
    eye_center = ((left_eye[0] + right_eye[0]) // 2, (left_eye[1] + right_eye[1]) // 2)
    angle = compute_angle(left_eye, right_eye)

    smooth_angle = smooth_value(smooth_angle, angle)

    # get Rotation matrix
    M = cv2.getRotationMatrix2D(eye_center, smooth_angle, 1.0)

    # apply affine transformation
    aligned_face = cv2.warpAffine(roi_frame, M, (width, height), flags=cv2.INTER_CUBIC)
    return aligned_face


def smooth_value(prev, new, alpha=0.3):
    if prev is None:
        return new
    return prev * (1 - alpha) + alpha * new


def expand_bbox(x, y, w, h, img_width, img_height, margin=0.3):
    # margin: 0.3 means 30% extra on each side
    dw = int(w * margin)
    dh = int(h * margin)
    nx = max(x - dw, 0)
    ny = max(y - dh, 0)
    nw = min(w + 2 * dw, img_width - nx)
    nh = min(h + 2 * dh, img_height - ny)
    return nx, ny, nw, nh


def preprocess_aligned_face(aligned_face: np.ndarray):
    # Convert BGR (OpenCV) to RGB
    rgb_face = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
    # Convert to PIL Image
    pil_face = Image.fromarray(rgb_face)
    # Resize to 160x160
    pil_face = pil_face.resize((160, 160))
    # Convert to numpy array
    np_face = np.array(pil_face)
    # Use torch.from_numpy and permute to channel-first
    face_tensor = torch.as_tensor(np_face, dtype=torch.float32).permute(2, 0, 1).float() / 255.0
    face_tensor = face_tensor.to("cuda")
    # Add batch dimension
    face_tensor = face_tensor.unsqueeze(0)
    return face_tensor


def get_embedding(resnet, aligned_face: np.ndarray):
    face_tensor = preprocess_aligned_face(aligned_face)
    with torch.no_grad():
        embedding = resnet(face_tensor)
    embedding = embedding.cpu().numpy()
    return embedding[0]  # shape: (512,)

def video_stream_embeddings(names, embeddings_db):
    cap = cv2.VideoCapture(0)

    face_detector = cv2.FaceDetectorYN.create(
        "dl_models/face_detection_yunet_2023mar_int8bq.onnx", "", (320, 320), score_threshold=0.7
    )
    resnet = InceptionResnetV1(pretrained="vggface2").eval()
    resnet = resnet.to("cuda")

    i = 0
    aligned_face = None
    while True:
        ret, frame = cap.read()

        if ret:
            height, width = frame.shape[:2]
            face_detector.setInputSize((width, height))
            _, faces = face_detector.detect(frame)

            if faces is not None:
                i += 1
                print(f"face detected: {i} times")
                for face in faces:
                    x, y, w, h = map(int, face[:4])
                    left_eye = tuple(map(int, face[4:6]))
                    right_eye = tuple(map(int, face[6:8]))

                    # region of interest
                    # roi_frame = frame[y:y+h+1, x:x+w+1]
                    nx, ny, nw, nh = expand_bbox(x, y, w, h, width, height, margin=0.3)
                    roi_frame = frame[ny : ny + nh, nx : nx + nw]

                    # Adjust eyes to ROI coordinates
                    # roi_left_eye = (left_eye[0] - x, left_eye[1] - y)
                    # roi_right_eye = (right_eye[0] - x, right_eye[1] - y)
                    roi_left_eye = (left_eye[0] - nx, left_eye[1] - ny)
                    roi_right_eye = (right_eye[0] - nx, right_eye[1] - ny)

                    # align face
                    aligned_face = align_face(roi_frame, roi_left_eye, roi_right_eye)
                    
                    if aligned_face is None or aligned_face.size == 0:
                        print("Warning: aligned face is None or empty, skipping.")
                        continue
                    # draw markers
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(frame, (left_eye[0], left_eye[1]), 5, (255, 0, 0), -1)
                    cv2.circle(frame, (right_eye[0], right_eye[1]), 5, (255, 0, 0), -1)

                    # get embeddings
                    embedding = get_embedding(resnet, aligned_face)
                    # if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
                    #     print(" Invalid embedding: contains NaN or Inf. Skipping...")
                    #     continue

                    print(embedding.shape)
                    print(embedding)


        else:
            print("Failed to capture the frame...")

        # display the image
        cv2.imshow("frame", frame)
        key = cv2.waitKey(50)
        if key is ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()



def load_embeddings_from_json(path_json_file):
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


path_json_file = "faces_embeddings_data.json"
names, embeddings_db = load_embeddings_from_json(path_json_file)
# print(names, embeddings_database)

smooth_angle = None
video_stream_embeddings(names, embeddings_db)