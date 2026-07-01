#!/usr/bin/env python3
"""Real-time SAM2 video tracking via webcam — HuggingFace Transformers API.

Controls:
  r  — draw bounding box on the current frame, then start tracking
  q  — quit

Windows:
  "Live"      — raw camera feed (always running)
  "SAM2 Mask" — frame with green mask overlay and red centroid cross
"""
from __future__ import annotations

import os

# Use China HuggingFace mirror for faster downloads
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import Sam2VideoModel, Sam2VideoProcessor

CAMERA_ID: int = 0
MODEL_ID: str = (
    "/home/mira/workspaces/lerobot_ws/src/deep_learning_models"
    "/models/raw_models/sam2_large"
)
OBJ_ID: int = 1
MASK_ALPHA: float = 0.45  # opacity of the green overlay
INFER_SIZE: tuple[int, int] = (640, 480)  # (W, H) — resize frames before SAM2 inference


# ── helpers ───────────────────────────────────────────────────────────────────

def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model(device: str) -> tuple[Sam2VideoModel, Sam2VideoProcessor]:
    print(f"Loading {MODEL_ID} on {device} ...")
    dtype = torch.float16 if device == "cuda" else torch.float32
    processor: Sam2VideoProcessor = Sam2VideoProcessor.from_pretrained(MODEL_ID)
    model: Sam2VideoModel = Sam2VideoModel.from_pretrained(
        MODEL_ID, device_map=device, torch_dtype=dtype
    )
    model.eval()
    print("Model ready.")
    return model, processor


def draw_roi(frame: np.ndarray) -> tuple[int, int, int, int] | None:
    """Freeze frame and let user draw a bounding box with the mouse.

    Returns (x, y, w, h) or None if the user cancels.
    """
    display = frame.copy()
    cv2.putText(
        display,
        "Drag to draw bbox  |  SPACE/ENTER = confirm  |  C = cancel",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2,
    )
    x, y, w, h = cv2.selectROI("Live", display, fromCenter=False, showCrosshair=True)
    return (x, y, w, h) if w > 0 and h > 0 else None


# ── SAM2 streaming API ────────────────────────────────────────────────────────

def init_session(
    frame: np.ndarray,
    bbox_xywh: tuple[int, int, int, int],
    model: Sam2VideoModel,
    processor: Sam2VideoProcessor,
    device: str,
) -> tuple[object, np.ndarray]:
    """Create a new streaming inference session and process the first frame.

    input_boxes format expected by add_inputs_to_inference_session:
      list[list[list[float]]]  →  [[[x1, y1, x2, y2]]]
      (1 frame  ×  1 object  ×  4 coords)

    Returns (session, binary_mask) where mask has shape (H, W) and dtype uint8.
    """
    x, y, w, h = bbox_xywh

    # Scale bbox from original frame coords to INFER_SIZE coords
    orig_h, orig_w = frame.shape[:2]
    sx, sy = INFER_SIZE[0] / orig_w, INFER_SIZE[1] / orig_h
    box: list[list[list[float]]] = [[[
        x * sx, y * sy, (x + w) * sx, (y + h) * sy
    ]]]

    infer_frame = cv2.resize(frame, INFER_SIZE)
    pil = Image.fromarray(cv2.cvtColor(infer_frame, cv2.COLOR_BGR2RGB))
    inputs = processor(images=pil, return_tensors="pt").to(device)

    # No video argument → streaming mode (frames arrive one at a time)
    session = processor.init_video_session(inference_device=device)

    processor.add_inputs_to_inference_session(
        inference_session=session,
        frame_idx=0,
        obj_ids=OBJ_ID,
        input_boxes=box,
        original_size=(INFER_SIZE[1], INFER_SIZE[0]),  # (H, W) of the resized frame
    )

    with torch.no_grad(), torch.autocast(device_type=device, dtype=torch.float16, enabled=(device == "cuda")):
        out = model(inference_session=session, frame=inputs.pixel_values[0])

    # post_process_masks returns a list; index [0] gives shape (num_objects, 1, H, W)
    masks = processor.post_process_masks(
        [out.pred_masks],
        original_sizes=inputs.original_sizes,
        binarize=True,
    )[0]

    mask: np.ndarray = masks[0, 0].cpu().numpy().astype(np.uint8)
    return session, mask


def track_frame(
    frame: np.ndarray,
    session: object,
    model: Sam2VideoModel,
    processor: Sam2VideoProcessor,
    device: str,
) -> np.ndarray:
    """Propagate the SAM2 tracker to the next webcam frame.

    The session manages its own internal frame counter; no frame_idx needed here.
    Returns binary mask (H, W) as uint8 (0 or 1).
    """
    infer_frame = cv2.resize(frame, INFER_SIZE)
    pil = Image.fromarray(cv2.cvtColor(infer_frame, cv2.COLOR_BGR2RGB))
    inputs = processor(images=pil, return_tensors="pt").to(device)

    with torch.no_grad(), torch.autocast(device_type=device, dtype=torch.float16, enabled=(device == "cuda")):
        out = model(inference_session=session, frame=inputs.pixel_values[0])

    masks = processor.post_process_masks(
        [out.pred_masks],
        original_sizes=inputs.original_sizes,
        binarize=True,
    )[0]

    return masks[0, 0].cpu().numpy().astype(np.uint8)


# ── visualisation ─────────────────────────────────────────────────────────────

def apply_overlay(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return a copy of frame with a green mask overlay and red centroid cross."""
    out = frame.copy()
    # Upscale mask to match display frame if sizes differ (inference uses INFER_SIZE)
    if mask.shape[:2] != frame.shape[:2]:
        mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)

    green_layer = np.zeros_like(frame, dtype=np.uint8)
    green_layer[mask == 1] = (0, 255, 0)
    out = cv2.addWeighted(out, 1.0 - MASK_ALPHA, green_layer, MASK_ALPHA, 0)

    ys, xs = np.nonzero(mask)
    if len(xs) > 0:
        cx, cy = int(xs.mean()), int(ys.mean())
        cv2.drawMarker(out, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, 24, 2)

    return out


# ── main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    device = get_device()
    if device == "cuda":
        torch.backends.cudnn.benchmark = True
    model, processor = load_model(device)

    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {CAMERA_ID}")
        return

    session: object | None = None
    mask: np.ndarray | None = None
    tracking: bool = False

    # skip_track is True for the one loop iteration right after init_session.
    # init_session already called model() for that frame and returned its mask,
    # so we must NOT call track_frame() again on the same frame.
    skip_track: bool = False

    print("Press 'r' to draw a bounding box and start tracking.")
    print("Press 'q' to quit.")

    while True:
        ret, raw_frame = cap.read()
        if not ret:
            print("Camera read failed — exiting.")
            break

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        if key == ord("r"):
            bbox = draw_roi(raw_frame.copy())
            if bbox is not None:
                print(f"Bbox {bbox} — initialising SAM2 ...")
                session, mask = init_session(raw_frame, bbox, model, processor, device)
                tracking = True
                skip_track = True
                print("Tracking started.")
            else:
                print("Bbox cancelled.")

        if tracking and session is not None:
            if skip_track:
                skip_track = False  # use the mask that came from init_session
            else:
                mask = track_frame(raw_frame, session, model, processor, device)

        # ── display ───────────────────────────────────────────────────────────
        cv2.imshow("Live", raw_frame)

        if tracking and mask is not None:
            cv2.imshow("SAM2 Mask", apply_overlay(raw_frame, mask))
        else:
            info = raw_frame.copy()
            cv2.putText(
                info,
                "Press 'r' to select an object",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            cv2.imshow("SAM2 Mask", info)

    cap.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
