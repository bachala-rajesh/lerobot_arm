#!/usr/bin/env python3
"""Detect AprilTags from the OAK-D RGB stream, and solve for the camera's pose
relative to the robot base.

Resulting TF tree:
    follower_base_link -> oak-d-base-frame -> ... -> oak_rgb_camera_optical_frame -> tag36h11:1
                       ^^^^^^^^^^^^^^^^^^^
                       the edge we are solving for
"""

from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share_dir = get_package_share_directory("apriltags_localization")

    config_path = os.path.join(share_dir, "config", "real_apriltags_config.yaml")
    calib_path = os.path.join(share_dir, "config", "base_to_camera_calib.yaml")

    # Subscribes compressed image + camera_info, publishes /detections_apriltags
    # and one TF per tag: oak_rgb_camera_optical_frame -> tag36h11:<id>
    detection_node = Node(
        package="apriltag_ros",
        executable="apriltag_node",
        name="apriltag_detection_node",
        output="screen",
        parameters=[config_path],
        remappings=[
            # config sets image_transport: compressed, so remap the /compressed topic
            ("/image_rect/compressed", "/oak/rgb/image_raw/compressed"),
            ("/camera_info", "/oak/rgb/camera_info"),
            ("/detections", "/detections_apriltags"),
        ],
        emulate_tty=True,
    )

    # Reads the tag's measured pose from calib_path, reads optical -> tag off /tf,
    # and publishes the one edge nothing else knows: follower_base_link -> oak-d-base-frame
    localizer_node = Node(
        package="apriltags_localization",
        executable="apriltag_world_localizer.py",  # installed via install(PROGRAMS ...), keeps the .py
        name="apriltag_world_localizer",
        output="screen",
        parameters=[{"config_file_path": calib_path}],
        emulate_tty=True,
    )

    return LaunchDescription([detection_node, localizer_node])
