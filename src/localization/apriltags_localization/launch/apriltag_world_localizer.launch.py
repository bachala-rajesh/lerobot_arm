#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_path = get_package_share_directory("apriltags_localization")
    config_path = os.path.join(pkg_path, "config", "tag_poses_in_world.yaml")

    localizer_node = Node(
        package="apriltags_localization",
        executable="apriltag_world_localizer.py",
        name="apriltag_world_localizer",
        parameters=[{"config_file_path": config_path}],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription([localizer_node])
