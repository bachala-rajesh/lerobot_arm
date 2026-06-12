"""Launch the VLM service node with params + image-topic remap."""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("vlm")
    default_config = os.path.join(pkg_share, "config", "vlm.yaml")

    # --- launch args ---
    config_arg = DeclareLaunchArgument(
        "config_file",
        default_value=default_config,
        description="Path to vlm.yaml parameter file.",
    )
    image_topic_arg = DeclareLaunchArgument(
        "image_topic",
        default_value="/oak/rgb/image_raw/compressed",
        description="Source CompressedImage topic (remapped to image_compressed).",
    )

    # --- node ---
    vlm_node = Node(
        package="vlm",
        executable="vlm_node",
        name="vlm_node",
        output="screen",
        parameters=[LaunchConfiguration("config_file")],
        remappings=[
            ("image_compressed", LaunchConfiguration("image_topic")),
        ],
    )

    return LaunchDescription([
        config_arg, 
        image_topic_arg, 
        vlm_node
        ])
