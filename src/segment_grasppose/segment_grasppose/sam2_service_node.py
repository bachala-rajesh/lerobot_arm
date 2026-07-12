#!/usr/bin/env python3
"""SAM2 service node.

Same SAM2 as sam2_scene_node, but runs ON DEMAND via a service instead of a
timer. It keeps the latest camera frame; when a request arrives it segments the
asked object and returns the mask.

Flow:
  1. Subscribe to the camera image, keep the latest frame.
  2. On a SegmentObject request:
       - use bbox_xyxy if given, else look the label up in scene_db
       - run SAM2 with that bbox on the latest frame
       - return the mask + centroid + score
  3. No window here — the test client shows the picture.

Params:
  image_topic  (str)  default: /oak/rgb/image_raw/compressed

Service:
  /segment_object   (project_interfaces/srv/SegmentObject)
"""

from __future__ import annotations

from contextlib import nullcontext
from typing import Optional

import cv2
import numpy as np
import torch
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from scene_db import SceneDB
from project_interfaces.srv import SegmentObject

# large checkpoint already present in this workspace; config must match (large -> l)
CHECKPOINT = (
    "/workspaces/lerobot_ws/src/deep_learning_models/"
    "models/raw_models/sam2_large/sam2.1_hiera_large.pt"
)
CONFIG = "configs/sam2.1/sam2.1_hiera_l.yaml"


class Sam2ServiceNode(Node):
    def __init__(self) -> None:
        super().__init__("sam2_service")

        self.declare_parameter("image_topic", "/oak/rgb/image_raw/compressed")
        image_topic = (
            self.get_parameter("image_topic").get_parameter_value().string_value
        )

        self._latest: Optional[CompressedImage] = None
        self._db = SceneDB()
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

        self.get_logger().info(f"loading SAM2 ({self._device}) ...")
        self._predictor = SAM2ImagePredictor(
            build_sam2(CONFIG, CHECKPOINT, device=self._device)
        )
        self.get_logger().info("SAM2 ready")

        # /oak/rgb/image_raw/compressed is a CompressedImage (raw topic is dead over Cyclone DDS)
        self._sub = self.create_subscription(
            CompressedImage, image_topic, self._image_cb, 10
        )
        self._srv = self.create_service(
            SegmentObject, "segment_object", self._on_request
        )
        self.get_logger().info(f"subscribed: {image_topic}")
        self.get_logger().info("service ready: /segment_object")

    def _image_cb(self, msg: CompressedImage) -> None:
        self._latest = msg

    def _on_request(
        self, req: SegmentObject.Request, res: SegmentObject.Response
    ) -> SegmentObject.Response:
        msg = self._latest
        if msg is None:
            res.success = False
            res.message = "no camera frame yet — wait for a moment"
            return res

        # 1) get the bbox: explicit bbox_xyxy wins, else scene_db lookup by label
        if len(req.bbox_xyxy) == 4:
            x1, y1, x2, y2 = (int(v) for v in req.bbox_xyxy)
        else:
            rows = self._db.query_by_label(label=req.label, limit=1)
            if not rows:
                res.success = False
                res.message = f"no '{req.label}' in scene_db (and no bbox given)"
                return res
            x1, y1, x2, y2 = rows[0].bbox

        # 2) decode the compressed frame (cv2 → no cv_bridge → keeps NumPy 2.x)
        arr = np.frombuffer(msg.data, np.uint8)
        rgb = cv2.cvtColor(cv2.imdecode(arr, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        box = np.array([x1, y1, x2, y2], dtype=np.float32)

        # 3) run SAM2
        autocast = (
            torch.autocast("cuda", dtype=torch.bfloat16)
            if self._device == "cuda"
            else nullcontext()
        )
        with torch.inference_mode(), autocast:
            self._predictor.set_image(rgb)
            masks, scores, _ = self._predictor.predict(
                box=box, multimask_output=False
            )
        mask = masks[0].astype(np.uint8)  # 0/1, shape (H, W)
        h, w = mask.shape

        # 4) centroid of the mask (guard empty mask)
        ys, xs = np.nonzero(mask)
        if xs.size:
            cu, cv_ = float(xs.mean()), float(ys.mean())
        else:
            cu, cv_ = -1.0, -1.0

        res.success = True
        res.message = f"segmented '{req.label}' bbox=({x1},{y1},{x2},{y2})"
        res.mask_flat = mask.flatten().tolist()  # ponytail: tolist is fine at test scale
        res.mask_height = int(h)
        res.mask_width = int(w)
        res.centroid_u = cu
        res.centroid_v = cv_
        res.score = float(scores[0])
        self.get_logger().info(res.message)
        return res


def main() -> None:
    rclpy.init()
    node = Sam2ServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
