#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description() -> LaunchDescription:

    #####################
    # Paths
    #####################
    pkg_bringup = get_package_share_directory("so101_bringup")
    pkg_description = get_package_share_directory("so101_description")
    pkg_control = get_package_share_directory("so101_control")

    controllers_yaml = os.path.join(pkg_control, "config", "so101_controllers.yaml")
    leader_calibration = os.path.join(
        pkg_bringup, "config", "so101_leader_calibration.yaml"
    )
    description_launch_path = os.path.join(
        pkg_description, "launch", "leader_description.launch.py"
    )

    #####################
    # Launch args
    #####################
    sim_mode = LaunchConfiguration("sim_mode", default="real_robot")
    use_sim_time = LaunchConfiguration("use_sim_time", default="false")
    leader_usb_port = LaunchConfiguration(
        "leader_usb_port", default="/dev/lerobot_leader"
    )
    leader_command = LaunchConfiguration("leader_command", default="false")

    #####################
    # Description (scene + both arm RSPs + static TFs)
    #####################
    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(description_launch_path),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "sim_mode": "real_robot",
            "leader_usb_port": leader_usb_port,
            "leader_command": leader_command,
            "leader_joint_config_file": leader_calibration,
        }.items(),
    )

    # control node
    control_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_control, "launch", "leader_joints_states.launch.py")
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "sim_mode": sim_mode,
        }.items(),
    )

    #####################
    # LaunchDescription
    #####################
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "leader_usb_port",
                default_value="/dev/lerobot_leader",
                description="Serial port for the leader arm",
            ),
            DeclareLaunchArgument(
                "leader_command",
                default_value="false",
                description="Enable command interface for the leader arm",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use sim time if true",
            ),
            description_launch,
            control_node,
        ]
    )
