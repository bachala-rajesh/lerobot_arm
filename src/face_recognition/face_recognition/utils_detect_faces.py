import cv2
import numpy as np
from PIL import Image
import torch
import torchvision.transforms as transforms
from pathlib import Path
import sys
import math


def preprocess_aligned_face(aligned_face: np.ndarray, device):
    rgb_face = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)

    transform = transforms.Compose([transforms.ToPILImage(), transforms.Resize((160, 160)), transforms.ToTensor()])

    face_tensor = transform(rgb_face).unsqueeze(0).to(device)
    return face_tensor


def get_embedding(model, aligned_face: np.ndarray, device):
    face_tensor = preprocess_aligned_face(aligned_face, device)
    with torch.no_grad():
        embedding = model(face_tensor)
    embedding = embedding.cpu().numpy()
    return embedding[0]  # shape: (512,)


def is_file_exists(file_path):
    if file_path.exists():
        print(f"the model path is : {file_path}")
        return True
    else:
        print(f"the file {file_path.name} does not exists at the location: {file_path.parent}")
        sys.exit(1)
        return False


def compute_angle_from_eyes(left_eye, right_eye):
    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]

    # find angle and convert radians into degrees
    angle = math.degrees(math.atan2(dy, dx))

    return angle


def smooth_value(prev, new, alpha=0.3):
    if prev is None:
        return new
    return prev * (1 - alpha) + alpha * new


def align_face_smooth_angle(roi_frame, left_eye, right_eye, smooth_angle):
    height, width = roi_frame.shape[:2]
    eye_center = ((left_eye[0] + right_eye[0]) // 2, (left_eye[1] + right_eye[1]) // 2)
    angle = compute_angle_from_eyes(left_eye, right_eye)

    smooth_angle = smooth_value(smooth_angle, angle)

    # get Rotation matrix
    M = cv2.getRotationMatrix2D(eye_center, smooth_angle, 1.0)

    # apply affine transformation
    aligned_face = cv2.warpAffine(roi_frame, M, (width, height), flags=cv2.INTER_CUBIC)
    return aligned_face, smooth_angle


def align_face(roi_frame, left_eye, right_eye):
    height, width = roi_frame.shape[:2]
    eye_center = ((left_eye[0] + right_eye[0]) // 2, (left_eye[1] + right_eye[1]) // 2)
    angle = compute_angle_from_eyes(left_eye, right_eye)

    # get Rotation matrix
    M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)

    # apply affine transformation
    aligned_face = cv2.warpAffine(roi_frame, M, (width, height), flags=cv2.INTER_CUBIC)
    return aligned_face


def expand_bbox(x, y, w, h, img_width, img_height, margin=0.3):
    # margin: 0.3 means 30% extra on each side
    dw = int(w * margin)
    dh = int(h * margin)
    nx = max(x - dw, 0)
    ny = max(y - dh, 0)
    nw = min(w + 2 * dw, img_width - nx)
    nh = min(h + 2 * dh, img_height - ny)
    return nx, ny, nw, nh