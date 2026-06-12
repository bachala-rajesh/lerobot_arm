#!/usr/bin/env python3
"""Launch the scene_localizer node with its YAML config."""
from __future__ import annotations

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = Path(get_package_share_directory("scene_localizer"))
    default_config = pkg_share / "config" / "scene_localizer.yaml"

    config_arg = DeclareLaunchArgument(
        "config_file",
        default_value=str(default_config),
        description="Path to the scene_localizer YAML config.",
    )

    localizer_node = Node(
        package="scene_localizer",
        executable="localizer_node",
        name="localizer_node",
        output="screen",
        parameters=[LaunchConfiguration("config_file")],
    )

    return LaunchDescription([config_arg, localizer_node])
