#!/usr/bin/env python3
from __future__ import annotations

import base64
import os
import threading

import cv2
import numpy as np
from dashscope import MultiModalConversation

MAIN_WINDOW = "Camera Feed (click to capture)"
CAPTURE_WINDOW = "Captured Frame + VLM Response"
MODEL = "qwen-vl-plus"
PROMPT = "Describe what you see in this image in  three to five sentences."

API_KEY = os.environ.get("DASHSCOPE_API_KEY")


def frame_to_base64(frame: np.ndarray) -> str:
    _, buffer = cv2.imencode(".jpg", frame)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode("utf-8")


def call_qwen(frame: np.ndarray, state: dict) -> None:
    """Runs in a background thread — calls Qwen-VL and stores the response."""
    try:
        img_data = frame_to_base64(frame)
        response = MultiModalConversation.call(
            model=MODEL,
            api_key=API_KEY,
            messages=[{
                "role": "user",
                "content": [
                    {"image": img_data},
                    {"text": PROMPT},
                ],
            }],
        )
        text = response.output.choices[0].message.content[0]["text"]
    except Exception as e:
        text = f"Error: {e}"

    print(f"\n[VLM Response]\n{text}\n")
    state["response"] = text
    state["busy"] = False


def draw_response(frame: np.ndarray, text: str) -> np.ndarray:
    """Draws wrapped response text on a copy of the frame."""
    canvas = frame.copy()
    h, w = canvas.shape[:2]

    # Semi-transparent dark bar at the bottom
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, h - 120), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)

    # Wrap text manually into lines of ~60 chars
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= 60:
            current = current + " " + word if current else word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = h - 110
    for line in lines[:4]:  # show max 4 lines
        cv2.putText(canvas, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1, cv2.LINE_AA)
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
        "response": None,
        "busy": False,
        "captured": None,
    }
    cv2.setMouseCallback(MAIN_WINDOW, on_mouse_click, state)

    print("Camera open. Click the video window to send frame to Qwen-VL. Press Escape or 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break

        state["frame"] = frame

        # New click — show "Analyzing..." and start API call in background
        if state["pending"] is not None:
            captured = state["pending"]
            state["captured"] = captured
            state["pending"] = None
            state["busy"] = True
            state["response"] = None

            analyzing = draw_response(captured, "Analyzing...")
            cv2.imshow(CAPTURE_WINDOW, analyzing)

            thread = threading.Thread(target=call_qwen, args=(captured, state), daemon=True)
            thread.start()

        # Response arrived — redraw capture window with text overlay
        if state["response"] is not None and state["captured"] is not None:
            result_frame = draw_response(state["captured"], state["response"])
            cv2.imshow(CAPTURE_WINDOW, result_frame)
            state["response"] = None  # consumed

        cv2.imshow(MAIN_WINDOW, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
