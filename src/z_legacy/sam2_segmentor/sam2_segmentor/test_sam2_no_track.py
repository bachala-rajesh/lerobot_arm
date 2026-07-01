#!/usr/bin/env python3
"""Test SAM2 action server — single-shot mode (track=false).

Steps:
  1. Read the most-recent detection from scene_db.
  2. Send that bbox to sam2/segment with track=false.
  3. Print result: score, centroid, mask pixel count.
"""

from __future__ import annotations

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from scene_db import SceneDB
from project_interfaces.action import SegmentObject


class NoTrackTestClient(Node):
    def __init__(self) -> None:
        super().__init__("sam2_no_track_test")
        self._client = ActionClient(self, SegmentObject, "sam2/segment")

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
                "Action server not available after 10s. Is sam2_node running?"
            )
            return

        # ── 3. build goal ──────────────────────────────────────────
        goal = SegmentObject.Goal()
        goal.bbox_xyxy = [x1, y1, x2, y2]
        goal.label = det.label
        goal.track = False

        self.get_logger().info(f"Sending goal: bbox={goal.bbox_xyxy} track=False")

        # ── 4. send and wait ───────────────────────────────────────
        send_future = self._client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)

        goal_handle = send_future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by server.")
            return

        self.get_logger().info("Goal accepted. Waiting for result...")

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        res = result_future.result().result

        # ── 5. print result ────────────────────────────────────────
        if not res.success:
            self.get_logger().error(f"Failed: {res.message}")
            return

        mask_pixels = sum(res.mask_flat)
        total_pixels = res.mask_height * res.mask_width

        print("\n── SAM2 Result ─────────────────────────────")
        print(f"  label      : {det.label}")
        print(f"  bbox       : {det.bbox}")
        print(f"  score      : {res.score:.3f}")
        print(f"  centroid   : u={res.centroid_u:.1f}  v={res.centroid_v:.1f}")
        print(f"  mask size  : {res.mask_width} x {res.mask_height}")
        print(
            f"  mask pixels: {mask_pixels} / {total_pixels}  ({100 * mask_pixels / max(total_pixels, 1):.1f}%)"
        )
        print("────────────────────────────────────────────\n")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = NoTrackTestClient()
    node.run()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
