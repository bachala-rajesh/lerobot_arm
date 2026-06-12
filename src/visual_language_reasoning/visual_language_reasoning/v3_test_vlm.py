#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

MODEL = "qwen3-vl-flash"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = os.environ.get("DASHSCOPE_API_KEY")

# Single combined prompt — one API call instead of two
COMBINED_PROMPT = (
    "Analyze this image. Respond with JSON only — no markdown, no extra text.\n"
    "Format:\n"
    '{"description": "3-5 sentence description", '
    '"detections": [{"label": "object name", "bbox_2d": [x1,y1,x2,y2]}]}\n'
    "bbox_2d coordinates are in 0-1000 scale (not pixels)."
)


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


def parse_response(raw: str, img_w: int, img_h: int) -> tuple[str, list[Detection]]:
    """
    Parse combined JSON response.
    Strips <think>...</think> blocks (qwen3 thinking mode) and ```json``` code fences.
    Coordinates are 0-1000 normalized → scale to actual frame pixels.
    """
    # Strip thinking blocks if qwen3 thinking mode is active
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Strip markdown code fence if present
    match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
    json_str = match.group(1) if match else cleaned

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"  [Warning] Could not parse JSON: {json_str[:200]}")
        return cleaned, []

    description: str = data.get("description", "")
    raw_detections: list = data.get("detections", [])

    detections: list[Detection] = []
    for item in raw_detections:
        label = item.get("label", "object")
        bbox = item.get("bbox_2d") or item.get("bbox") or item.get("box")
        if not bbox or len(bbox) < 4:
            continue
        x1 = max(0, min(int(bbox[0] / 1000 * img_w), img_w - 1))
        y1 = max(0, min(int(bbox[1] / 1000 * img_h), img_h - 1))
        x2 = max(0, min(int(bbox[2] / 1000 * img_w), img_w - 1))
        y2 = max(0, min(int(bbox[3] / 1000 * img_h), img_h - 1))
        detections.append(Detection(label, x1, y1, x2, y2))

    return description, detections


def call_vlm(frame: np.ndarray, state: dict, resize: tuple[int, int] | None = None) -> None:
    """Background thread — single API call for description + detections.

    resize: (width, height) to shrink frame before sending to VLM.
            Bounding boxes are always mapped back to original frame size.
    """
    h, w = frame.shape[:2]  # original dims — used for bbox mapping
    vlm_frame = cv2.resize(frame, resize) if resize else frame
    if resize:
        print(f"  [VLM input size: {resize[0]}x{resize[1]}]")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    try:
        img_data = frame_to_base64(vlm_frame)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_data}},
                    {"type": "text", "text": COMBINED_PROMPT},
                ],
            }],
        )
        raw = response.choices[0].message.content
        description, detections = parse_response(raw, w, h)
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
        cv2.rectangle(canvas,
                      (det.x1, label_bg_y),
                      (det.x1 + len(det.label) * 10 + 6, det.y1),
                      (0, 255, 0), -1)
        cv2.putText(canvas, det.label, (det.x1 + 3, det.y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

    # Semi-transparent black bar at the bottom for text
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, h - 130), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)

    # Word-wrap description text into the bar
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
        cv2.putText(canvas, line, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)
        y += 22

    return canvas


def on_mouse_click(event: int, x: int, y: int, flags: int, state: dict) -> None:
    if event == cv2.EVENT_LBUTTONDOWN and state["frame"] is not None and not state["busy"]:
        state["pending"] = state["frame"].copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VLM camera viewer — qwen3-vl-flash")
    parser.add_argument(
        "--resize",
        nargs=2,
        type=int,
        metavar=("WIDTH", "HEIGHT"),
        default=None,
        help="Resize frame before sending to VLM (e.g. --resize 640 480). "
             "Display stays full resolution.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    resize: tuple[int, int] | None = tuple(args.resize) if args.resize else None  # type: ignore[assignment]

    if not API_KEY:
        print("Error: DASHSCOPE_API_KEY environment variable is not set.")
        return

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Cannot open camera 1.")
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

    if resize:
        print(f"Camera 1 open. Model: {MODEL}  |  VLM input: {resize[0]}x{resize[1]}")
    else:
        print(f"Camera 1 open. Model: {MODEL}  |  VLM input: original resolution")
    print("Click the video window to send frame to VLM. Press 'q' or Escape to quit.")

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
            threading.Thread(target=call_vlm, args=(captured, state, resize), daemon=True).start()

        if state["description"] is not None and state["captured"] is not None:
            result = draw_result(state["captured"], state["description"], state["detections"] or [])
            cv2.imshow(CAPTURE_WINDOW, result)
            state["description"] = None  # clear so it doesn't redraw every frame

        cv2.imshow(MAIN_WINDOW, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
