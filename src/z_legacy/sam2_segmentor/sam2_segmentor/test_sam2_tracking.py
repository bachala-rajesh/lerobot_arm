#!/usr/bin/env python3
"""Test SAM2 action server — tracking mode (track=true).

Steps:
  1. Read most-recent detection from scene_db.
  2. Send bbox to sam2/segment with track=true.
  3. Print centroid feedback every frame for TRACK_SECONDS.
  4. Cancel the goal cleanly.
"""

from __future__ import annotations

import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from scene_db import SceneDB
from project_interfaces.action import SegmentObject

# How long to run tracking before cancelling
TRACK_SECONDS: float = 10.0


class TrackingTestClient(Node):
    def __init__(self) -> None:
        super().__init__("sam2_tracking_test")
        self._client = ActionClient(self, SegmentObject, "sam2/segment")
        self._goal_handle = None
        self._frame_count = 0
        self._start_time: float = 0.0

    def _feedback_cb(self, feedback_msg) -> None:
        fb = feedback_msg.feedback
        elapsed = time.time() - self._start_time
        print(
            f"  [{elapsed:5.1f}s] frame={fb.frame_count:4d}  "
            f"centroid=({fb.centroid_u:6.1f}, {fb.centroid_v:6.1f})  "
            f"score={fb.score:.3f}"
        )
        self._frame_count = fb.frame_count

    def run(self) -> None:
        # ── 1. read bbox from scene_db ─────────────────────────────
        db = SceneDB()
        rows = db.query_recent(limit=1)
        db.close()

        if not rows:
            self.get_logger().error("scene_db is empty. Run VLM node first.")
            return

        det = rows[0]
        x1, y1, x2, y2 = det.bbox
        self.get_logger().info(
            f"DB row id={det.id}  label='{det.label}'  bbox={det.bbox}"
        )

        # ── 2. wait for action server ──────────────────────────────
        self.get_logger().info("Waiting for sam2/segment action server...")
        if not self._client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(
                "Action server not available. Is sam2_node running?"
            )
            return

        # ── 3. build goal ──────────────────────────────────────────
        goal = SegmentObject.Goal()
        goal.bbox_xyxy = [x1, y1, x2, y2]
        goal.label = det.label
        goal.track = True

        self.get_logger().info(
            f"Sending tracking goal: bbox={goal.bbox_xyxy}  "
            f"Will cancel after {TRACK_SECONDS}s."
        )

        # ── 4. send goal ───────────────────────────────────────────
        send_future = self._client.send_goal_async(
            goal, feedback_callback=self._feedback_cb
        )
        rclpy.spin_until_future_complete(self, send_future)

        goal_handle = send_future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by server.")
            return

        self._goal_handle = goal_handle
        self._start_time = time.time()

        print("\n── SAM2 Tracking ───────────────────────────")
        print(f"  label  : {det.label}")
        print(f"  bbox   : {det.bbox}")
        print(f"  Running for {TRACK_SECONDS}s ...\n")

        # ── 5. spin + wait for timeout ─────────────────────────────
        deadline = time.time() + TRACK_SECONDS
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)

        # ── 6. cancel ──────────────────────────────────────────────
        self.get_logger().info("Cancelling tracking goal...")
        cancel_future = goal_handle.cancel_goal_async()
        rclpy.spin_until_future_complete(self, cancel_future)

        # ── 7. wait for final result ───────────────────────────────
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        res = result_future.result().result

        # ── 8. summary ─────────────────────────────────────────────
        print("\n── Final Result ────────────────────────────")
        print(f"  message    : {res.message}")
        print(f"  total frames received : {self._frame_count}")
        if res.mask_height > 0:
            mask_pixels = sum(res.mask_flat)
            total_pixels = res.mask_height * res.mask_width
            print(f"  last score : {res.score:.3f}")
            print(f"  last centroid : ({res.centroid_u:.1f}, {res.centroid_v:.1f})")
            print(
                f"  last mask  : {mask_pixels}/{total_pixels} px ({100 * mask_pixels / max(total_pixels, 1):.1f}%)"
            )
        print("────────────────────────────────────────────\n")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TrackingTestClient()
    node.run()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
