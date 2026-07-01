#!/usr/bin/env python3
"""
Test SAM2.1 segmentation with a bbox prompt.

Downloads a test image (truck from SAM2 official examples).
Runs SAM2 with a bbox covering the truck.
Saves result image with green mask overlay.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import cv2
import numpy as np
import torch
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

# ── paths ──────────────────────────────────────────────────────────────────
MODEL_DIR  = Path("/home/mira/workspaces/lerobot_ws/src/deep_learning_models/models/raw_models/sam2")
CHECKPOINT = MODEL_DIR / "sam2.1_hiera_large.pt"
IMG_URL    = "https://raw.githubusercontent.com/facebookresearch/sam2/main/notebooks/images/truck.jpg"
IMG_PATH   = Path(__file__).parent / "test_image_truck.jpg"
OUT_PATH   = Path(__file__).parent / "test_result_sam2.jpg"

# ── 1. download image ──────────────────────────────────────────────────────
if not IMG_PATH.exists():
    print(f"Downloading: {IMG_URL}")
    urllib.request.urlretrieve(IMG_URL, IMG_PATH)
    print(f"Saved → {IMG_PATH}")
else:
    print(f"Image already exists: {IMG_PATH}")

# ── 2. load image ──────────────────────────────────────────────────────────
bgr = cv2.imread(str(IMG_PATH))
if bgr is None:
    raise RuntimeError(f"Could not read image: {IMG_PATH}")
rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
h, w = rgb.shape[:2]
print(f"Image size: {w}x{h}")

# ── 3. bbox prompt ─────────────────────────────────────────────────────────
# truck occupies roughly center-right of the image
# adjust these if you want to segment a different region
x1, y1, x2, y2 = int(w * 0.20), int(h * 0.30), int(w * 0.85), int(h * 0.95)
bbox = np.array([x1, y1, x2, y2])
print(f"Bbox prompt: {bbox}")

# ── 4. load SAM2 ──────────────────────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

# "configs/sam2.1/sam2.1_hiera_l.yaml" is the registered name inside sam2 package
sam2_model = build_sam2(
    config_file="configs/sam2.1/sam2.1_hiera_l.yaml",
    ckpt_path=str(CHECKPOINT),
    device=device,
)
predictor = SAM2ImagePredictor(sam2_model)
print("SAM2 model loaded.")

# ── 5. run segmentation ────────────────────────────────────────────────────
predictor.set_image(rgb)   # encodes image once

masks, scores, _ = predictor.predict(
    box=bbox,
    multimask_output=False,   # return 1 best mask
)

mask = masks[0].astype(bool)   # shape (H, W)
print(f"Mask shape:  {mask.shape}")
print(f"Score:       {scores[0]:.3f}")
print(f"Mask pixels: {mask.sum()} / {mask.size}  ({100*mask.mean():.1f}% of image)")

# ── 6. visualize ───────────────────────────────────────────────────────────
overlay = bgr.copy()

# green tint on masked pixels
green = np.zeros_like(overlay)
green[:, :] = (0, 200, 0)
overlay[mask] = cv2.addWeighted(overlay, 0.5, green, 0.5, 0)[mask]

# blue bbox
cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 100, 0), 3)

# score label
cv2.putText(overlay, f"score: {scores[0]:.2f}", (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 100, 0), 2)

cv2.imwrite(str(OUT_PATH), overlay)
print(f"Result saved → {OUT_PATH}")
