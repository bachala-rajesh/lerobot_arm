#!/usr/bin/env python3
"""Launch the SAM2 service node (sam2_service).

  ros2 launch segment_grasppose sam2_service.launch.py
  ros2 launch segment_grasppose sam2_service.launch.py image_topic:=/my/rgb/compressed
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    image_topic = LaunchConfiguration("image_topic")

    sam2_service = Node(
        package="segment_grasppose",
        executable="sam2_service_node",  # matches CMakeLists RENAME
        name="sam2_server",
        output="screen",
        parameters=[{"image_topic": image_topic}],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "image_topic",
            default_value="/oak/rgb/image_raw/compressed",
            description="Compressed RGB topic SAM2 reads frames from",
        ),
        sam2_service,
    ])
