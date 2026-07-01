#!/usr/bin/env python3
"""
Fist Detector — MediaPipe Tasks API
=====================================
Uses mp.tasks.vision.HandLandmarker (mediapipe >= 0.10.5).
Downloads hand_landmarker.task model on first run (~8 MB).

Dependencies:
    pip install mediapipe opencv-python numpy

Press ESC to quit.
"""

import os
import time
import urllib.request
from collections import deque

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # index
    (0, 9), (9, 10), (10, 11), (11, 12),   # middle
    (0, 13), (13, 14), (14, 15), (15, 16), # ring
    (0, 17), (17, 18), (18, 19), (19, 20), # pinky
    (5, 9), (9, 13), (13, 17),             # palm
]

FINGERS = [
    (8, 6),   # index tip vs PIP
    (12, 10), # middle tip vs PIP
    (16, 14), # ring tip vs PIP
    (20, 18), # pinky tip vs PIP
]


def _download_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand_landmarker.task (~8 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"Saved to {MODEL_PATH}")


class FistDetector:
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, history_size: int = 5):
        _download_model()

        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_index}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self.pos_history = deque(maxlen=history_size)
        self.fist_history = deque(maxlen=history_size)
        self.fist_active = False
        self.hand_visible = False
        self.smooth_pos = None
        self._start_time = time.monotonic()

        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def _timestamp_ms(self) -> int:
        return int((time.monotonic() - self._start_time) * 1000)

    def is_fist(self, landmarks) -> bool:
        wrist = np.array([landmarks[0].x, landmarks[0].y])
        folded = 0
        for tip_id, pip_id in FINGERS:
            tip = np.array([landmarks[tip_id].x, landmarks[tip_id].y])
            pip = np.array([landmarks[pip_id].x, landmarks[pip_id].y])
            if np.linalg.norm(tip - wrist) < np.linalg.norm(pip - wrist) * 1.08:
                folded += 1

        # Thumb: tip (4) closer to index MCP (5) than thumb IP (3) is
        thumb_tip = np.array([landmarks[4].x, landmarks[4].y])
        thumb_ip = np.array([landmarks[3].x, landmarks[3].y])
        index_mcp = np.array([landmarks[5].x, landmarks[5].y])
        thumb_folded = np.linalg.norm(thumb_tip - index_mcp) < np.linalg.norm(thumb_ip - index_mcp)

        return folded >= 3 and thumb_folded

    def get_hand_center(self, landmarks):
        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        hand_size = np.linalg.norm(
            np.array([wrist.x, wrist.y]) - np.array([middle_mcp.x, middle_mcp.y])
        )
        return wrist.x, wrist.y, hand_size

    def smooth(self, pos: tuple) -> tuple:
        self.pos_history.append(pos)
        return tuple(np.array(self.pos_history).mean(axis=0))

    def _draw_landmarks(self, frame, landmarks, h, w, color):
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (255, 0, 0), 2)
        for pt in pts:
            cv2.circle(frame, pt, 3, color, -1)

    def update(self, frame):
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        output = {"hand_visible": False, "fist": False, "position": None, "smooth_position": None}

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect_for_video(mp_image, self._timestamp_ms())

        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            self.hand_visible = True

            raw_fist = self.is_fist(landmarks)
            self.fist_history.append(raw_fist)
            self.fist_active = sum(self.fist_history) > len(self.fist_history) / 2

            x, y, depth = self.get_hand_center(landmarks)
            self.smooth_pos = self.smooth((x, y, depth))

            output.update({
                "hand_visible": True,
                "fist": self.fist_active,
                "position": (x, y, depth),
                "smooth_position": self.smooth_pos,
            })

            color = (0, 255, 0) if self.fist_active else (0, 165, 255)
            self._draw_landmarks(frame, landmarks, h, w, color)

            cx, cy = int(x * w), int(y * h)
            cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 20, 2)
            cv2.circle(frame, (cx, cy), 8, color, -1)

            if self.fist_active:
                status = "FIST DETECTED"
                sub = f"Active | ({x:.2f}, {y:.2f}, d:{depth:.2f})"
            else:
                status = "HAND OPEN"
                sub = "Close fist to activate"

            cv2.putText(frame, status, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            cv2.putText(frame, sub, (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        else:
            self.hand_visible = False
            self.fist_active = False
            self.fist_history.clear()
            cv2.putText(
                frame, "NO HAND DETECTED", (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2,
            )

        return frame, output

    def run(self):
        print("=" * 50)
        print("Fist Detector Started")
        print("Show your hand. Close into a FIST to activate.")
        print("Press ESC to quit.")
        print("=" * 50)

        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue

            annotated, data = self.update(frame)

            if data["fist"] and data["smooth_position"] is not None:
                x, y, d = data["smooth_position"]
                print(f"\rFIST | x={x:.3f} y={y:.3f} depth={d:.3f}   ", end="", flush=True)
            elif not data["hand_visible"]:
                print("\rNO HAND                                          ", end="", flush=True)
            else:
                print("\rHAND OPEN (waiting for fist)                     ", end="", flush=True)

            cv2.imshow("Fist Detector", annotated)
            if cv2.waitKey(1) & 0xFF == 27:
                break

        self.shutdown()

    def shutdown(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.detector.close()
        print("\nShutdown complete.")


if __name__ == "__main__":
    detector = FistDetector(camera_index=0, width=640, height=480, history_size=5)
    detector.run()
