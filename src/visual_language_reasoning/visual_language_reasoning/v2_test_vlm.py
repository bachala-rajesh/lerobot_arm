#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import threading
from dataclasses import dataclass

import cv2
import numpy as np
from openai import OpenAI

MAIN_WINDOW = "Camera Feed (click to capture)"
CAPTURE_WINDOW = "Captured Frame + VLM Response"

# Correct model name for Qwen2.5-VL on DashScope
MODEL = "qwen-vl-max"  # change to "qwen2.5-vl-7b-instruct" after activating in Alibaba Cloud console

DESCRIPTION_PROMPT = "Describe what you see in this image in three to five sentences."

# Qwen2.5-VL returns JSON with bbox_2d: [x1,y1,x2,y2] in 0-1000 normalized coords
GROUNDING_PROMPT = (
    "Detect all visible objects in this image. "
    "Output a JSON array where each entry has 'label' and 'bbox_2d' (x1,y1,x2,y2 in 0-1000 scale). "
    "Example: [{\"label\": \"cup\", \"bbox_2d\": [100, 200, 300, 400]}]"
)

API_KEY = os.environ.get("DASHSCOPE_API_KEY")
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


@dataclass
class Detection:
    label: str
    x1: int
    y1: int
    x2: int
    y2: int


def frame_to_base64(frame: np.ndarray) -> str:
    _, buffer = cv2.imencode(".jpg", frame)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode("utf-8")


def parse_json_response(raw: str, img_w: int, img_h: int) -> list[Detection]:
    """
    Parses the grounding JSON response from Qwen2.5-VL.
    Handles both raw JSON and ```json ... ``` code blocks.
    Coordinates are 0-1000 normalized → scale to actual frame pixels.
    """
    # Strip markdown code block if present
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    json_str = match.group(1) if match else raw.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"  [Warning] Could not parse JSON: {json_str[:200]}")
        return []

    if not isinstance(data, list):
        data = [data]

    detections: list[Detection] = []
    for item in data:
        label = item.get("label", "object")
        bbox = item.get("bbox_2d") or item.get("bbox") or item.get("box")
        if not bbox or len(bbox) < 4:
            continue
        # Scale from 0-1000 to actual frame pixels and clamp
        x1 = max(0, min(int(bbox[0] / 1000 * img_w), img_w - 1))
        y1 = max(0, min(int(bbox[1] / 1000 * img_h), img_h - 1))
        x2 = max(0, min(int(bbox[2] / 1000 * img_w), img_w - 1))
        y2 = max(0, min(int(bbox[3] / 1000 * img_h), img_h - 1))
        detections.append(Detection(label, x1, y1, x2, y2))

    return detections


def _call(client: OpenAI, img_data: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": img_data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return response.choices[0].message.content


def call_qwen(frame: np.ndarray, state: dict) -> None:
    """Runs in a background thread — two calls: description + grounding."""
    h, w = frame.shape[:2]
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    try:
        img_data = frame_to_base64(frame)
        description = _call(client, img_data, DESCRIPTION_PROMPT)
        raw_grounding = _call(client, img_data, GROUNDING_PROMPT)
        detections = parse_json_response(raw_grounding, w, h)
    except Exception as e:
        description = f"Error: {e}"
        detections = []

    print(f"\n[VLM Description]\n{description}")
    if detections:
        print("\n[Detected Objects]")
        for det in detections:
            print(f"  {det.label}: ({det.x1},{det.y1}) -> ({det.x2},{det.y2})")
    else:
        print("  [No detections parsed]")
    print()

    state["description"] = description
    state["detections"] = detections
    state["busy"] = False


def draw_result(frame: np.ndarray, text: str, detections: list[Detection]) -> np.ndarray:
    canvas = frame.copy()
    h, w = canvas.shape[:2]

    for det in detections:
        cv2.rectangle(canvas, (det.x1, det.y1), (det.x2, det.y2), (0, 255, 0), 2)
        label_bg_y = max(det.y1 - 20, 0)
        cv2.rectangle(canvas, (det.x1, label_bg_y),
                      (det.x1 + len(det.label) * 10 + 6, det.y1), (0, 255, 0), -1)
        cv2.putText(canvas, det.label, (det.x1 + 3, det.y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, h - 130), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)

    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= 70:
            current = current + " " + word if current else word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = h - 120
    for line in lines[:5]:
        cv2.putText(canvas, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.50, (255, 255, 255), 1, cv2.LINE_AA)
        y += 22

    return canvas


def on_mouse_click(event: int, x: int, y: int, flags: int, state: dict) -> None:
    if event == cv2.EVENT_LBUTTONDOWN and state["frame"] is not None and not state["busy"]:
        state["pending"] = state["frame"].copy()


def main() -> None:
    if not API_KEY:
        print("Error: DASHSCOPE_API_KEY environment variable is not set.")
        return

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Cannot open camera.")
        return

    cv2.namedWindow(MAIN_WINDOW, cv2.WINDOW_NORMAL)
    cv2.namedWindow(CAPTURE_WINDOW, cv2.WINDOW_NORMAL)

    state: dict = {
        "frame": None,
        "pending": None,
        "captured": None,
        "description": None,
        "detections": None,
        "busy": False,
    }
    cv2.setMouseCallback(MAIN_WINDOW, on_mouse_click, state)

    print("Camera open. Click video window to send to Qwen2.5-VL. Press Escape or 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break

        state["frame"] = frame

        if state["pending"] is not None:
            captured = state["pending"]
            state["captured"] = captured
            state["pending"] = None
            state["busy"] = True
            state["description"] = None
            state["detections"] = None

            cv2.imshow(CAPTURE_WINDOW, draw_result(captured, "Analyzing...", []))
            threading.Thread(target=call_qwen, args=(captured, state), daemon=True).start()

        if state["description"] is not None and state["captured"] is not None:
            result = draw_result(state["captured"], state["description"], state["detections"] or [])
            cv2.imshow(CAPTURE_WINDOW, result)
            state["description"] = None

        cv2.imshow(MAIN_WINDOW, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
