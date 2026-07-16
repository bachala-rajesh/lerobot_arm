#!/usr/bin/env python3
"""Launch both service nodes: SAM2 segmentation + AnyGrasp grasp pose.

Starts:
  sam2_service_node   -> /segment_object     (SAM2)
  grasppose_server    -> /find_grasp_pose     (AnyGrasp)

Run inside the anygrasp env (robotics_layer2 docker), because grasppose_server
loads gsnet + torch. Both nodes load big models, so give them a few seconds.

  ros2 launch segment_grasppose grasp_services.launch.py
  ros2 launch segment_grasppose grasp_services.launch.py table_min_height:=0.01
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    image_topic = LaunchConfiguration("image_topic")
    table_min_height = LaunchConfiguration("table_min_height")

    sam2_service = Node(
        package="segment_grasppose",
        executable="sam2_service_node",  # matches CMakeLists RENAME
        name="sam2_server",
        output="screen",
        parameters=[{"image_topic": image_topic}],
    )

    grasppose_server = Node(
        package="segment_grasppose",
        executable="grasppose_server",
        name="grasppose_server",
        output="screen",
        parameters=[{"table_min_height": table_min_height}],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "image_topic",
            default_value="/oak/rgb/image_raw/compressed",
            description="Compressed RGB topic SAM2 reads frames from",
        ),
        DeclareLaunchArgument(
            "table_min_height",
            default_value="0.0",
            description="Keep points this far (m) above the tag. 0.0 = cut at table",
        ),
        sam2_service,
        grasppose_server,
    ])
