#!/usr/bin/env python3
"""Real-time SAM2 segmentation test — VIDEO PREDICTOR mode.

Uses SAM2VideoPredictor with chunk-based streaming:
  1. Collect CHUNK_SIZE frames from camera
  2. Process entire chunk with video predictor (temporal memory across frames)
  3. Display results at 30 fps
  4. Next chunk: use last mask as prompt → temporal continuity across chunks
  Repeat.

Press 'q' to quit.

Edit CAMERA_ID and BBOX to match your setup.
"""
from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from sam2.build_sam import build_sam2_video_predictor

# ── config ─────────────────────────────────────────────────────────────────
CAMERA_ID   = 0
BBOX        = [160, 120, 480, 360]  # [x1, y1, x2, y2] in pixels
CHUNK_SIZE  = 10                    # frames per chunk — lower = less latency
OBJ_ID      = 1                     # object id for SAM2 tracker

MODEL_CONFIG = "configs/sam2.1/sam2.1_hiera_l.yaml"
CHECKPOINT   = Path(
    "/home/mira/workspaces/lerobot_ws/src/deep_learning_models"
    "/models/raw_models/sam2/sam2.1_hiera_large.pt"
)

# ── load model ─────────────────────────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
print("Loading SAM2 video predictor ...")

predictor = build_sam2_video_predictor(MODEL_CONFIG, str(CHECKPOINT), device=device)
print("SAM2 video predictor loaded.\n")

# ── open camera ────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(CAMERA_ID)
if not cap.isOpened():
    raise RuntimeError(f"Cannot open camera id={CAMERA_ID}")
print("Camera opened.")

# ── temp dir (reused each chunk) ───────────────────────────────────────────
BASE_TEMP = Path(tempfile.mkdtemp())

def save_frames_to_dir(frames: list[np.ndarray]) -> Path:
    """Save BGR frames as numbered JPEGs. SAM2 init_state reads this dir."""
    chunk_dir = BASE_TEMP / "chunk"
    if chunk_dir.exists():
        shutil.rmtree(chunk_dir)
    chunk_dir.mkdir()
    for i, bgr in enumerate(frames):
        cv2.imwrite(str(chunk_dir / f"{i:05d}.jpg"), bgr)
    return chunk_dir


def process_chunk(
    frames: list[np.ndarray],
    bbox: list[int],
    prev_mask: np.ndarray | None,
) -> list[np.ndarray | None]:
    """Run video predictor on one chunk. Returns one bool mask per frame."""
    chunk_dir = save_frames_to_dir(frames)
    h, w = frames[0].shape[:2]

    with torch.inference_mode():
        state = predictor.init_state(str(chunk_dir))
        predictor.reset_state(state)  # clear any leftover state

        if prev_mask is None:
            # First chunk — prompt with bbox
            predictor.add_new_points_or_box(
                inference_state=state,
                frame_idx=0,
                obj_id=OBJ_ID,
                box=np.array(bbox, dtype=np.float32),
            )
        else:
            # Subsequent chunks — prompt frame 0 with last mask from prev chunk
            prompt_mask = cv2.resize(
                prev_mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST
            ).astype(bool)
            predictor.add_new_mask(
                inference_state=state,
                frame_idx=0,
                obj_id=OBJ_ID,
                mask=prompt_mask,
            )

        # Propagate through all frames in chunk
        masks_out: list[np.ndarray | None] = [None] * len(frames)
        for frame_idx, _obj_ids, mask_logits in predictor.propagate_in_video(state):
            # mask_logits shape: (1, 1, H, W)
            mask = (mask_logits[0, 0] > 0.0).cpu().numpy().astype(bool)
            masks_out[frame_idx] = mask

    return masks_out


# ── draw helpers ───────────────────────────────────────────────────────────
def overlay_mask(bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = bgr.copy()
    green = np.zeros_like(out)
    green[mask] = [0, 200, 0]
    out[mask] = cv2.addWeighted(out, 0.5, green, 0.5, 0)[mask]
    return out

def draw_centroid(img: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return 0.0, 0.0
    cu, cv_ = float(xs.mean()), float(ys.mean())
    cv2.drawMarker(img, (int(cu), int(cv_)), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
    return cu, cv_


# ── main loop ──────────────────────────────────────────────────────────────
x1, y1, x2, y2 = BBOX
chunk_buffer: list[np.ndarray] = []
prev_mask: np.ndarray | None = None
proc_fps: float = 0.0
chunk_num: int = 0

print("Running. Press 'q' to quit.\n")

quit_flag = False
while not quit_flag:
    ret, bgr = cap.read()
    if not ret:
        print("Camera read failed.")
        break

    chunk_buffer.append(bgr.copy())

    # ── live preview while collecting ──────────────────────────────
    preview = bgr.copy()
    cv2.rectangle(preview, (x1, y1), (x2, y2), (255, 80, 0), 2)
    cv2.putText(preview, f"Collecting {len(chunk_buffer)}/{CHUNK_SIZE}  [video mode]",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2)
    if proc_fps > 0:
        cv2.putText(preview, f"proc: {proc_fps:.1f} FPS",
                    (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.imshow("SAM2 Video Mode", preview)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

    if len(chunk_buffer) < CHUNK_SIZE:
        continue

    # ── process chunk ─────────────────────────────────────────────
    t0 = time.time()
    try:
        masks = process_chunk(chunk_buffer, BBOX, prev_mask)
    except Exception as e:
        print(f"Chunk {chunk_num} error: {e}")
        chunk_buffer.clear()
        prev_mask = None
        continue

    elapsed = time.time() - t0
    proc_fps = CHUNK_SIZE / max(elapsed, 1e-6)
    chunk_num += 1

    # Save last valid mask for next chunk's prompt
    for m in reversed(masks):
        if m is not None:
            prev_mask = m
            break

    # ── replay chunk at ~30 fps ───────────────────────────────────
    for i, (frame_bgr, mask) in enumerate(zip(chunk_buffer, masks)):
        if mask is not None:
            vis = overlay_mask(frame_bgr, mask)
            cu, cv_ = draw_centroid(vis, mask)
            cv2.putText(vis, f"centroid ({cu:.0f}, {cv_:.0f})",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            cv2.putText(vis, f"mask: {mask.sum()} px",
                        (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        else:
            vis = frame_bgr.copy()

        cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 80, 0), 2)
        cv2.putText(vis, f"chunk {chunk_num}  f{i+1}/{CHUNK_SIZE}  proc {proc_fps:.1f} FPS",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.imshow("SAM2 Video Mode", vis)
        if cv2.waitKey(33) & 0xFF == ord("q"):  # 33ms ≈ 30 fps
            quit_flag = True
            break

    chunk_buffer.clear()

# ── cleanup ────────────────────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindows()
shutil.rmtree(BASE_TEMP, ignore_errors=True)
print("Done.")
