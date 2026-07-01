#!/usr/bin/env python3
"""SAM2 segmentation action server.

Action: sam2/segment  (so101_interfaces/action/SegmentObject)

Goal:
  bbox_xyxy  — [x1, y1, x2, y2] in camera pixel space
  label      — object name (for logging)
  track      — false = one shot; true = run on every new frame + publish feedback

Result:
  mask_flat, mask_height, mask_width — flattened binary mask
  centroid_u, centroid_v             — pixel centroid of mask
  score                              — SAM2 confidence

Feedback (only when track=true):
  centroid_u, centroid_v, score, frame_count
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
import torch
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

from so101_interfaces.action import SegmentObject


class SAM2Node(Node):
    def __init__(self) -> None:
        super().__init__("sam2_node")

        # ── params ────────────────────────────────────────────────
        self.declare_parameter(
            "model_config", "configs/sam2.1/sam2.1_hiera_l.yaml"
        )
        self.declare_parameter(
            "checkpoint",
            "/home/mira/workspaces/lerobot_ws/src/deep_learning_models/"
            "models/raw_models/sam2/sam2.1_hiera_large.pt",
        )
        self.declare_parameter("image_topic", "/oak/rgb/image_raw/compressed")
        self.declare_parameter("device", "cuda")

        gp = self.get_parameter
        cfg = gp("model_config").get_parameter_value().string_value
        ckpt = gp("checkpoint").get_parameter_value().string_value
        topic = gp("image_topic").get_parameter_value().string_value
        device = gp("device").get_parameter_value().string_value

        # ── load SAM2 ─────────────────────────────────────────────
        self.get_logger().info(f"Loading SAM2: {ckpt}")
        if not Path(ckpt).exists():
            raise FileNotFoundError(f"Checkpoint not found: {ckpt}")

        sam2_model = build_sam2(cfg, ckpt, device=device)
        self._predictor = SAM2ImagePredictor(sam2_model)
        self._predict_lock = threading.Lock()  # SAM2 not thread-safe
        self.get_logger().info("SAM2 loaded.")

        # ── frame cache ───────────────────────────────────────────
        self._frame: np.ndarray | None = None   # RGB HxWx3
        self._frame_seq: int = 0                # increments each new frame
        self._frame_lock = threading.Lock()

        # ── ROS ───────────────────────────────────────────────────
        cb = ReentrantCallbackGroup()

        self._img_sub = self.create_subscription(
            CompressedImage, topic, self._image_cb, 10, callback_group=cb
        )

        self._action_server = ActionServer(
            self,
            SegmentObject,
            "sam2/segment",
            execute_callback=self._execute,
            goal_callback=lambda _: GoalResponse.ACCEPT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=cb,
        )

        self.get_logger().info(f"SAM2Node ready. Image topic: {topic}")

    # ── image subscriber ──────────────────────────────────────────
    def _image_cb(self, msg: CompressedImage) -> None:
        arr = np.frombuffer(msg.data, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        with self._frame_lock:
            self._frame = rgb
            self._frame_seq += 1

    def _get_frame(self) -> tuple[np.ndarray | None, int]:
        with self._frame_lock:
            return (None if self._frame is None else self._frame.copy()), self._frame_seq

    # ── action execute ────────────────────────────────────────────
    def _execute(self, goal_handle) -> SegmentObject.Result:
        req = goal_handle.request
        bbox = np.array(req.bbox_xyxy, dtype=np.float32)
        label = req.label
        track = req.track

        self.get_logger().info(
            f"Segment goal: label='{label}' bbox={bbox.tolist()} track={track}"
        )

        # wait up to 3 s for a camera frame
        frame, seq = self._wait_for_frame(timeout=3.0)
        if frame is None:
            self.get_logger().error("No camera frame received. Aborting.")
            goal_handle.abort()
            res = SegmentObject.Result()
            res.success = False
            res.message = "no camera frame"
            return res

        if not track:
            return self._single_shot(goal_handle, frame, bbox)
        else:
            return self._tracking(goal_handle, bbox, seq)

    # ── single-shot mode ──────────────────────────────────────────
    def _single_shot(
        self,
        goal_handle,
        frame: np.ndarray,
        bbox: np.ndarray,
    ) -> SegmentObject.Result:
        mask, score = self._segment(frame, bbox)
        cu, cv_ = self._centroid(mask)

        res = SegmentObject.Result()
        res.success = True
        res.message = "ok"
        res.mask_flat = mask.flatten().astype(np.uint8).tolist()
        res.mask_height, res.mask_width = int(mask.shape[0]), int(mask.shape[1])
        res.centroid_u = float(cu)
        res.centroid_v = float(cv_)
        res.score = float(score)
        goal_handle.succeed()
        self.get_logger().info(f"Single-shot done. score={score:.3f} centroid=({cu:.1f},{cv_:.1f})")
        return res

    # ── tracking mode ─────────────────────────────────────────────
    def _tracking(
        self,
        goal_handle,
        bbox: np.ndarray,
        init_seq: int,
    ) -> SegmentObject.Result:
        count = 0
        last_seq = init_seq - 1   # ensures first frame always processed
        mask: np.ndarray | None = None
        cu, cv_, score = 0.0, 0.0, 0.0

        while not goal_handle.is_cancel_requested:
            frame, seq = self._get_frame()
            if frame is None or seq == last_seq:
                time.sleep(0.02)
                continue
            last_seq = seq

            mask, score = self._segment(frame, bbox)
            cu, cv_ = self._centroid(mask)
            count += 1

            fb = SegmentObject.Feedback()
            fb.centroid_u = float(cu)
            fb.centroid_v = float(cv_)
            fb.score = float(score)
            fb.frame_count = count
            goal_handle.publish_feedback(fb)

        goal_handle.canceled()
        self.get_logger().info(f"Tracking stopped after {count} frames.")

        res = SegmentObject.Result()
        res.success = True
        res.message = f"tracking stopped after {count} frames"
        if mask is not None:
            res.mask_flat = mask.flatten().astype(np.uint8).tolist()
            res.mask_height, res.mask_width = int(mask.shape[0]), int(mask.shape[1])
        res.centroid_u = float(cu)
        res.centroid_v = float(cv_)
        res.score = float(score)
        return res

    # ── helpers ───────────────────────────────────────────────────
    def _wait_for_frame(self, timeout: float) -> tuple[np.ndarray | None, int]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            frame, seq = self._get_frame()
            if frame is not None:
                return frame, seq
            time.sleep(0.05)
        return None, 0

    def _segment(self, frame: np.ndarray, bbox: np.ndarray) -> tuple[np.ndarray, float]:
        with self._predict_lock:
            self._predictor.set_image(frame)
            masks, scores, _ = self._predictor.predict(
                box=bbox, multimask_output=False
            )
        mask = masks[0].astype(bool)
        return mask, float(scores[0])

    def _centroid(self, mask: np.ndarray) -> tuple[float, float]:
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return 0.0, 0.0
        return float(xs.mean()), float(ys.mean())


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SAM2Node()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
