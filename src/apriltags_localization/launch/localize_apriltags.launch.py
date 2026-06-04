#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:

    use_sim_time = LaunchConfiguration("use_sim_time", default="false")

    pkg_path = get_package_share_directory("apriltags_localization")
    apriltag_config_path = os.path.join(
        pkg_path, "config", "real_apriltags_detections_config.yaml"
    )
    tag_poses_path = os.path.join(
        pkg_path, "config", "tag_poses_in_world.yaml"
    )

    # ----- Apriltag detection node (camera -> tag TFs) -----
    apriltag_detection_node = Node(
        package="apriltag_ros",
        executable="apriltag_node",
        name="apriltag_detection_node",
        output="screen",
        parameters=[
            apriltag_config_path,
            {"use_sim_time": use_sim_time},
        ],
        remappings=[
            ("/image_rect/compressed", "/oak/rgb/image_raw/compressed"),
            ("/camera_info", "/oak/rgb/camera_info"),
            ("/detections", "/detections_apriltags"),
        ],
        emulate_tty=True,
    )

    # ----- World localizer (world -> camera TF) -----
    world_localizer_node = Node(
        package="apriltags_localization",
        executable="apriltag_world_localizer.py",
        name="apriltag_world_localizer",
        output="screen",
        parameters=[
            {"config_file_path": tag_poses_path},
            {"use_sim_time": use_sim_time},
        ],
        emulate_tty=True,
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock if true",
            ),
            apriltag_detection_node,
            world_localizer_node,
        ]
    )
