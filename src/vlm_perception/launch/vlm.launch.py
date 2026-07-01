"""Launch the VLM service node with params + image-topic remap."""

from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("vlm_perception")
    default_config = os.path.join(pkg_share, "config", "vlm.yaml")

    # --- launch args ---
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use sim time if true.",
    )
    config_arg = DeclareLaunchArgument(
        "config_file",
        default_value=default_config,
        description="Path to vlm.yaml parameter file.",
    )
    image_topic_arg = DeclareLaunchArgument(
        "image_topic",
        default_value="/oak/rgb/image_raw/compressed",
        description="Source CompressedImage topic for real robot (remapped to image_compressed).",
    )

    common = dict(
        package="vlm_perception",
        executable="vlm_node",
        name="vlm_node",
        output="screen",
    )

    # sim: raw Image type  |  real: CompressedImage type
    vlm_node_sim = Node(
        **common,
        parameters=[LaunchConfiguration("config_file"), {"compressed": False}],
        remappings=[("image_compressed", "/oak/rgb/image_raw")],
        condition=IfCondition(LaunchConfiguration("use_sim_time")),
    )
    vlm_node_real = Node(
        **common,
        parameters=[LaunchConfiguration("config_file")],
        remappings=[("image_compressed", LaunchConfiguration("image_topic"))],
        condition=UnlessCondition(LaunchConfiguration("use_sim_time")),
    )

    return LaunchDescription(
        [
            use_sim_time_arg,
            config_arg,
            image_topic_arg,
            vlm_node_sim,
            vlm_node_real,
        ]
    )
