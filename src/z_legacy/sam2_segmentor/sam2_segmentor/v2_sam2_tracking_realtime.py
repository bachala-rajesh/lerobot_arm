#!/usr/bin/env python3
"""Real-time SAM2 video tracking — v2 with background inference thread.

Architecture:
  Main thread   — reads camera + displays at full camera FPS (never blocked)
  Worker thread — runs SAM2 inference in background, updates shared mask

If SAM2 takes 2s per frame, display still runs at 30 FPS.
The mask shown is always the most recently finished inference result.

Controls:
  r  — draw bounding box and start tracking
  q  — quit

Windows:
  "Live"      — raw camera feed
  "SAM2 Mask" — frame with green mask overlay, red centroid, and FPS counter
"""
from __future__ import annotations

import os
import threading
import time

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
MASK_ALPHA: float = 0.45
INFER_SIZE: tuple[int, int] = (640, 480)  # (W, H) passed to SAM2 — smaller = faster


# ── thread-safe tracking state ────────────────────────────────────────────────

class TrackingState:
    """Shared state between the main thread (display) and worker thread (SAM2)."""

    def __init__(self) -> None:
        self._mask: np.ndarray | None = None
        self._mask_lock = threading.Lock()

        self._frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()

        # Event fires when a new frame is ready for inference.
        # Worker clears it immediately after reading — so if it's busy,
        # the main thread just overwrites the frame without blocking.
        self.new_frame = threading.Event()
        self.stop = threading.Event()
        self.worker: threading.Thread | None = None
        self.infer_fps: float = 0.0

    # called by main thread every frame
    def put_frame(self, frame: np.ndarray) -> None:
        with self._frame_lock:
            self._frame = frame  # overwrite — always keep latest
        self.new_frame.set()

    # called by main thread for display
    def get_mask(self) -> np.ndarray | None:
        with self._mask_lock:
            return self._mask.copy() if self._mask is not None else None

    # called by worker thread after inference
    def set_mask(self, mask: np.ndarray) -> None:
        with self._mask_lock:
            self._mask = mask

    def stop_worker(self) -> None:
        """Signal the worker to stop and wait for it to finish."""
        self.stop.set()
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=5.0)
        # Reset for next tracking session
        self.stop.clear()
        self.new_frame.clear()
        self._mask = None
        self._frame = None
        self.infer_fps = 0.0


# ── model loading ─────────────────────────────────────────────────────────────

def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model(device: str) -> tuple[Sam2VideoModel, Sam2VideoProcessor]:
    print(f"Loading model on {device} ...")
    dtype = torch.float16 if device == "cuda" else torch.float32
    processor = Sam2VideoProcessor.from_pretrained(MODEL_ID)
    model = Sam2VideoModel.from_pretrained(MODEL_ID, device_map=device, torch_dtype=dtype)
    model.eval()
    print("Model ready.")
    return model, processor


# ── ROI drawing ───────────────────────────────────────────────────────────────

def draw_roi(frame: np.ndarray) -> tuple[int, int, int, int] | None:
    """Let user draw a bounding box. Returns (x, y, w, h) or None if cancelled."""
    display = frame.copy()
    cv2.putText(
        display,
        "Drag to draw bbox  |  SPACE/ENTER = confirm  |  C = cancel",
        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2,
    )
    x, y, w, h = cv2.selectROI("Live", display, fromCenter=False, showCrosshair=True)
    return (x, y, w, h) if w > 0 and h > 0 else None


# ── SAM2 helpers ──────────────────────────────────────────────────────────────

def _to_pil(frame: np.ndarray) -> Image.Image:
    """Resize to INFER_SIZE and convert BGR → RGB PIL image."""
    small = cv2.resize(frame, INFER_SIZE)
    return Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))


def init_session(
    frame: np.ndarray,
    bbox_xywh: tuple[int, int, int, int],
    model: Sam2VideoModel,
    processor: Sam2VideoProcessor,
    device: str,
) -> tuple[object, np.ndarray]:
    """Start a new streaming session with bbox on frame 0.

    Returns (session, initial_mask_HW).
    """
    x, y, w, h = bbox_xywh

    # Scale bbox from original frame coords to INFER_SIZE coords
    orig_h, orig_w = frame.shape[:2]
    sx, sy = INFER_SIZE[0] / orig_w, INFER_SIZE[1] / orig_h
    box: list[list[list[float]]] = [[[x * sx, y * sy, (x + w) * sx, (y + h) * sy]]]

    inputs = processor(images=_to_pil(frame), return_tensors="pt").to(device)

    # Streaming mode — no video argument; frames arrive one at a time
    session = processor.init_video_session(inference_device=device)
    processor.add_inputs_to_inference_session(
        inference_session=session,
        frame_idx=0,
        obj_ids=OBJ_ID,
        input_boxes=box,
        original_size=(INFER_SIZE[1], INFER_SIZE[0]),  # (H, W) of resized frame
    )

    with torch.no_grad(), torch.autocast(
        device_type=device, dtype=torch.float16, enabled=(device == "cuda")
    ):
        out = model(inference_session=session, frame=inputs.pixel_values[0])

    masks = processor.post_process_masks(
        [out.pred_masks], original_sizes=inputs.original_sizes, binarize=True
    )[0]  # shape: (num_objects, 1, H, W)

    return session, masks[0, 0].cpu().numpy().astype(np.uint8)


def track_frame(
    frame: np.ndarray,
    session: object,
    model: Sam2VideoModel,
    processor: Sam2VideoProcessor,
    device: str,
) -> np.ndarray:
    """Propagate tracker to the next frame. Returns binary mask (H, W)."""
    inputs = processor(images=_to_pil(frame), return_tensors="pt").to(device)
    with torch.no_grad(), torch.autocast(
        device_type=device, dtype=torch.float16, enabled=(device == "cuda")
    ):
        out = model(inference_session=session, frame=inputs.pixel_values[0])
    masks = processor.post_process_masks(
        [out.pred_masks], original_sizes=inputs.original_sizes, binarize=True
    )[0]
    return masks[0, 0].cpu().numpy().astype(np.uint8)


# ── worker thread ─────────────────────────────────────────────────────────────

def _worker(
    state: TrackingState,
    session: object,
    model: Sam2VideoModel,
    processor: Sam2VideoProcessor,
    device: str,
) -> None:
    """Runs in background. Waits for new frames, runs SAM2, stores mask."""
    while not state.stop.is_set():
        # Wait up to 50ms for a new frame — then re-check stop flag
        if not state.new_frame.wait(timeout=0.05):
            continue
        state.new_frame.clear()

        with state._frame_lock:
            frame = state._frame.copy() if state._frame is not None else None
        if frame is None:
            continue

        t0 = time.perf_counter()
        try:
            mask = track_frame(frame, session, model, processor, device)
            state.set_mask(mask)
            state.infer_fps = 1.0 / max(time.perf_counter() - t0, 1e-6)
        except Exception as exc:
            print(f"[Worker] Inference error: {exc}")


# ── visualisation ─────────────────────────────────────────────────────────────

def apply_overlay(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Green mask overlay + red centroid cross on frame."""
    out = frame.copy()
    # Upscale mask to display frame size if needed
    if mask.shape[:2] != frame.shape[:2]:
        mask = cv2.resize(
            mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST
        )
    green = np.zeros_like(frame, dtype=np.uint8)
    green[mask == 1] = (0, 255, 0)
    out = cv2.addWeighted(out, 1.0 - MASK_ALPHA, green, MASK_ALPHA, 0)
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

    state = TrackingState()
    tracking = False

    # Display-side FPS counter
    disp_t0 = time.perf_counter()
    disp_count = 0
    disp_fps = 0.0

    print("Press 'r' to draw a bounding box and start tracking.")
    print("Press 'q' to quit.")

    while True:
        ret, raw_frame = cap.read()
        if not ret:
            print("Camera read failed — exiting.")
            break

        # Update display FPS
        disp_count += 1
        elapsed = time.perf_counter() - disp_t0
        if elapsed >= 1.0:
            disp_fps = disp_count / elapsed
            disp_count = 0
            disp_t0 = time.perf_counter()

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        if key == ord("r"):
            # Stop any running worker before starting a new session
            state.stop_worker()
            tracking = False

            bbox = draw_roi(raw_frame.copy())
            if bbox is not None:
                print(f"Bbox {bbox} — initialising SAM2 ...")
                session, init_mask = init_session(raw_frame, bbox, model, processor, device)
                state.set_mask(init_mask)

                state.worker = threading.Thread(
                    target=_worker,
                    args=(state, session, model, processor, device),
                    daemon=True,
                )
                state.worker.start()
                tracking = True
                print("Tracking started — background thread running.")
            else:
                print("Bbox cancelled.")

        # Send latest frame to worker (non-blocking — overwrites if worker is busy)
        if tracking:
            state.put_frame(raw_frame)

        # ── display ──────────────────────────────────────────────────────────
        cv2.imshow("Live", raw_frame)

        if tracking:
            mask = state.get_mask()
            vis = apply_overlay(raw_frame, mask) if mask is not None else raw_frame.copy()
            cv2.putText(
                vis,
                f"Display {disp_fps:.0f} FPS  |  Infer {state.infer_fps:.1f} FPS",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
            )
            cv2.imshow("SAM2 Mask", vis)
        else:
            info = raw_frame.copy()
            cv2.putText(
                info, "Press 'r' to select an object",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
            )
            cv2.imshow("SAM2 Mask", info)

    state.stop_worker()
    cap.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
