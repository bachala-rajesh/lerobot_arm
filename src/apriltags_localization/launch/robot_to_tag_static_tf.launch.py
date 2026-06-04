#!/usr/bin/env python3

import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time", default="false")

    # Load calibration YAML
    pkg_path = get_package_share_directory("apriltags_localization")
    config_path = os.path.join(pkg_path, "config", "robot_to_tag_calibration.yaml")

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)["robot_to_tag_static_tf"]["ros__parameters"]

    # Static transform publisher: follower_base_link -> tag
    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="robot_to_tag_static_tf",
        arguments=[
            "--x",
            str(cfg["x"]),
            "--y",
            str(cfg["y"]),
            "--z",
            str(cfg["z"]),
            "--roll",
            str(cfg["roll"]),
            "--pitch",
            str(cfg["pitch"]),
            "--yaw",
            str(cfg["yaw"]),
            "--frame-id",
            cfg["parent_frame"],
            "--child-frame-id",
            cfg["child_frame"],
        ],
        parameters=[{"use_sim_time": use_sim_time}],
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use sim time if true",
            ),
            static_tf_node,
        ]
    )
