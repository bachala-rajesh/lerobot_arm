#!/usr/bin/env python3
"""Test client for /segment_grasppose/find_grasp_pose service."""
from __future__ import annotations

import sys

import rclpy
from rclpy.node import Node

from project_interfaces.srv import FindGraspPose

SERVICE = '/segment_grasppose/find_grasp_pose'


def call_service(node: Node, label: str, bboxes: list[float]) -> None:
    client = node.create_client(FindGraspPose, SERVICE)
    print(f'Waiting for {SERVICE} ...')
    if not client.wait_for_service(timeout_sec=5.0):
        print(f'ERROR: {SERVICE} not available. Is segment_grasppose_node running?')
        sys.exit(1)

    req = FindGraspPose.Request()
    req.object_label = label
    req.bboxes_xyxy = bboxes

    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)

    if not future.done():
        print('ERROR: service call timed out (10 s)')
        return

    res: FindGraspPose.Response = future.result()
    print(f'  success : {res.success}')
    print(f'  message : {res.message}')
    print(f'  poses   : {len(res.grasp_poses)}')
    for i, pose in enumerate(res.grasp_poses):
        p = pose.pose.position
        o = pose.pose.orientation
        print(f'    [{i}] pos=({p.x:.3f}, {p.y:.3f}, {p.z:.3f})  '
              f'quat=({o.x:.3f}, {o.y:.3f}, {o.z:.3f}, {o.w:.3f})')


def main() -> None:
    rclpy.init()
    node = Node('segment_grasppose_test_client')

    # Test A: pass bboxes directly (x1, y1, x2, y2)
    print('\n=== Test A: bboxes directly ===')
    call_service(node, label='', bboxes=[100.0, 100.0, 300.0, 300.0])

    # Test B: pass object label (scene_db lookup — will stub until wired)
    print('\n=== Test B: object_label="cup" ===')
    call_service(node, label='cup', bboxes=[])

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
