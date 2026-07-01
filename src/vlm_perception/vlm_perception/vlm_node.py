#!/usr/bin/env python3
"""
VLM service node — Qwen3-VL-Flash via Alibaba DashScope.

Service:  /vlm/detect_objects   (project_interfaces/srv/DetectObjects)
Subscribes to the latest camera frame, runs the VLM on demand, returns bboxes.
"""

from __future__ import annotations

import base64
import json
import os
import re
import threading
from dataclasses import dataclass

import cv2
import numpy as np
import rclpy
from builtin_interfaces.msg import Time as TimeMsg
from openai import OpenAI
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image

from scene_db import SceneDB
from project_interfaces.srv import DetectObjects


# ---------------------------------------------------------------- VLM config
MODEL = "qwen3-vl-flash"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

COMBINED_PROMPT_TEMPLATE = (
    "Examine the image and answer this question: {user_prompt}\n"
    "Respond with JSON only — no markdown, no extra text.\n"
    'Format: {{"description": "...", '
    '"detections": [{{"label": "...", "bbox_2d": [x1,y1,x2,y2]}}]}}\n'
    "Rules for description:\n"
    "  - Directly answer the question above.\n"
    "  - Mention spatial relations (behind, in front, on, next to),\n"
    "    colors, and counts when relevant to the question.\n"
    "  - Be factual. No markdown, no lists, no special characters.\n"
    "  - Aim for 1 to 3 plain sentences. This will be read aloud.\n"
    "Rules for detections:\n"
    "  - List every distinct visible object with its bbox_2d,\n"
    "    even objects not mentioned in the question.\n"
    "  - bbox_2d in 0-1000 scale."
)


@dataclass
class Detection:
    label: str
    x1: int
    y1: int
    x2: int
    y2: int


# ---------------------------------------------------------------- node
class VlmNode(Node):
    def __init__(self) -> None:
        super().__init__("vlm_node")

        # --- params (declare → read) ---
        self.declare_parameter("service_name", "/vlm/detect_objects")
        self.declare_parameter("resize", [640, 480])  # [w, h]; [] = no resize
        self.declare_parameter("api_key", "")  # "" → fall back to env var
        self.declare_parameter("write_to_db", True)
        self.declare_parameter("detector_name", "vlm")
        self.declare_parameter("source_frame", "oak_rgb_camera_optical_frame")
        self.declare_parameter("compressed", True)  # false = sim (raw Image)

        self._service_name: str = (
            self.get_parameter("service_name").get_parameter_value().string_value
        )
        resize_list: list[int] = list(
            self.get_parameter("resize").get_parameter_value().integer_array_value
        )
        self._resize: tuple[int, int] | None = (
            (resize_list[0], resize_list[1]) if len(resize_list) == 2 else None
        )
        yaml_key: str = self.get_parameter("api_key").get_parameter_value().string_value
        self._api_key: str | None = (
            os.environ.get(yaml_key)
            if yaml_key
            else os.environ.get("DASHSCOPE_API_KEY")
        )

        if not self._api_key:
            self.get_logger().error(
                "No API key:  set 'api_key' in YAML or DASHSCOPE_API_KEY env var."
            )

        self._write_to_db: bool = (
            self.get_parameter("write_to_db").get_parameter_value().bool_value
        )
        self._detector_name: str = (
            self.get_parameter("detector_name").get_parameter_value().string_value
        )
        self._source_frame: str = (
            self.get_parameter("source_frame").get_parameter_value().string_value
        )
        self._compressed: bool = (
            self.get_parameter("compressed").get_parameter_value().bool_value
        )

        # Open scene_db only if writing is enabled.
        self._db: SceneDB | None = SceneDB() if self._write_to_db else None
        if self._db is not None:
            self.get_logger().info(f"scene_db opened at {self._db.path}")

        self.get_logger().info(
            f"Params — service: {self._service_name}, resize: {self._resize}, "
            f"write_to_db: {self._write_to_db}, detector: {self._detector_name}, "
            f"source_frame: {self._source_frame}"
        )

        # --- state: (frame, header_stamp) under one lock ---
        self._latest_frame: np.ndarray | None = None
        self._latest_stamp: TimeMsg | None = None
        self._frame_lock = threading.Lock()

        # --- OpenAI client (reuse across calls) ---
        self._vlm_client = OpenAI(api_key=self._api_key, base_url=BASE_URL)

        # --- callback group ---
        cb_group = ReentrantCallbackGroup()

        if self._compressed:
            self._image_sub = self.create_subscription(
                CompressedImage,
                "image_compressed",
                self._image_cb,
                qos_profile=10,
                callback_group=cb_group,
            )
        else:
            self._image_sub = self.create_subscription(
                Image,
                "image_compressed",  # same internal name — remapped in launch
                self._image_raw_cb,
                qos_profile=10,
                callback_group=cb_group,
            )

        self._srv = self.create_service(
            DetectObjects,
            self._service_name,
            self._handle_detect,
            callback_group=cb_group,
        )

        self.get_logger().info(f"VLM node ready. Service: {self._service_name}")

    # -------------------------------------------------- callbacks
    def _image_cb(self, msg: CompressedImage) -> None:
        """Decode and cache the most recent frame + its stamp."""
        np_arr = np.frombuffer(msg.data, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return
        with self._frame_lock:
            self._latest_frame = frame
            self._latest_stamp = msg.header.stamp

    def _image_raw_cb(self, msg: Image) -> None:
        """For sim: decode raw Image (no cv_bridge — numpy only)."""
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, -1))
        if msg.encoding == "rgb8":
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        with self._frame_lock:
            self._latest_frame = frame.copy()
            self._latest_stamp = msg.header.stamp

    def _handle_detect(
        self, request: DetectObjects.Request, response: DetectObjects.Response
    ) -> DetectObjects.Response:
        """Service callback. Runs Qwen VLM on latest frame, returns bboxes."""
        # 1. snapshot
        with self._frame_lock:
            frame = None if self._latest_frame is None else self._latest_frame.copy()
            stamp = self._latest_stamp

        if frame is None:
            self.get_logger().warn("No camera frame received yet.")
            response.success = False
            response.description = "ERROR: no camera frame yet."
            return response

        # 2. record ORIGINAL size first — bbox coords must match this
        orig_h, orig_w = frame.shape[:2]

        # 3. resize copy that goes to the VLM (bboxes still mapped to ORIGINAL)
        vlm_frame = cv2.resize(frame, self._resize) if self._resize else frame

        # 4. blocking VLM call
        self.get_logger().info(f"Calling VLM with prompt: '{request.prompt}'")
        description, detections = self._call_qwen(
            vlm_frame, request.prompt, orig_w, orig_h
        )

        # 5. fill response
        response.success = True
        response.description = description
        response.labels = [d.label for d in detections]
        response.bboxes_xyxy = [v for d in detections for v in (d.x1, d.y1, d.x2, d.y2)]
        response.image_width = orig_w
        response.image_height = orig_h
        response.stamp = stamp if stamp is not None else TimeMsg()

        # 6. persist to scene_db (3D coords filled in later by the localizer)
        self._write_detections_to_db(detections, orig_w, orig_h, stamp)

        self.get_logger().info(f"Returned {len(detections)} detections.")
        return response

    # -------------------------------------------------- db write
    def _write_detections_to_db(
        self,
        detections: list[Detection],
        img_w: int,
        img_h: int,
        stamp: TimeMsg | None,
    ) -> None:
        """Insert each detection as a row with world_x = NULL.
        The localizer node will fill in 3D coords later."""
        if self._db is None or not detections:
            return

        detected_at = (
            stamp.sec + stamp.nanosec * 1e-9 if stamp is not None else None
        )
        try:
            for d in detections:
                self._db.insert_detection(
                    label=d.label,
                    bbox=(d.x1, d.y1, d.x2, d.y2),
                    image_size=(img_w, img_h),
                    source_frame=self._source_frame,
                    detector=self._detector_name,
                    detected_at=detected_at,
                )
            self.get_logger().info(
                f"Wrote {len(detections)} rows to scene_db."
            )
        except Exception as e:
            self.get_logger().error(f"scene_db write failed: {e}")

    # -------------------------------------------------- VLM call
    def _call_qwen(
        self, frame: np.ndarray, user_prompt: str, out_w: int, out_h: int
    ) -> tuple[str, list[Detection]]:
        """Blocking call to Qwen-VL via DashScope OpenAI-compatible API.

        out_w / out_h: dimensions the returned bboxes should be scaled to
        (the original frame size, NOT the resized VLM input).
        """
        try:
            img_data = self._frame_to_base64(frame)
            prompt = COMBINED_PROMPT_TEMPLATE.format(user_prompt=user_prompt)
            response = self._vlm_client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": img_data}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                
            )
            raw = response.choices[0].message.content
            return self._parse_response(raw, out_w, out_h)
        except Exception as e:
            self.get_logger().error(f"VLM call failed: {e}")
            return f"ERROR: VLM exception: {e}", []

    # -------------------------------------------------- helpers
    @staticmethod
    def _frame_to_base64(frame: np.ndarray) -> str:
        """JPEG-encode then base64-wrap as a data URL."""
        _, buffer = cv2.imencode(".jpg", frame)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode(
            "utf-8"
        )

    @staticmethod
    def _parse_response(
        raw: str, img_w: int, img_h: int
    ) -> tuple[str, list[Detection]]:
        """Strip <think>…</think> and ```json fences, json.loads,
        scale bbox from 0-1000 to pixels of (img_w, img_h).
        """
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        json_str = match.group(1) if match else cleaned

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return f"ERROR: VLM returned unparseable text: {cleaned[:80]}", []

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


# ---------------------------------------------------------------- entry
def main(args=None) -> None:
    rclpy.init(args=args)
    node = VlmNode()
    executor = MultiThreadedExecutor()  # image cb + service run concurrently
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    if node._db is not None:
        node._db.close()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
