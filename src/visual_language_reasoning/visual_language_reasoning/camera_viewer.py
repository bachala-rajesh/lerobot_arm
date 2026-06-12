#!/usr/bin/env python3
from __future__ import annotations

import cv2

MAIN_WINDOW = "Camera Feed (click to capture)"
CAPTURE_WINDOW = "Captured Frame"


def on_mouse_click(event: int, x: int, y: int, flags: int, state: dict) -> None:
    # Only store the frame on click — never call imshow/namedWindow here
    if event == cv2.EVENT_LBUTTONDOWN and state["frame"] is not None:
        state["pending"] = state["frame"].copy()


def main() -> None:
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Cannot open camera.")
        return

    cv2.namedWindow(MAIN_WINDOW, cv2.WINDOW_NORMAL)
    cv2.namedWindow(CAPTURE_WINDOW, cv2.WINDOW_NORMAL)

    state: dict = {"frame": None, "pending": None}
    cv2.setMouseCallback(MAIN_WINDOW, on_mouse_click, state)

    print("Camera open. Click the video window to capture a frame. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break

        state["frame"] = frame

        # Update the single capture window — never open a new one
        if state["pending"] is not None:
            cv2.imshow(CAPTURE_WINDOW, state["pending"])
            state["pending"] = None

        cv2.imshow(MAIN_WINDOW, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:  # 27 = Escape
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
