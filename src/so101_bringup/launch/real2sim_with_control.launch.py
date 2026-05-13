#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description() -> LaunchDescription:

    #####################
    # Paths
    #####################
    pkg_bringup = get_package_share_directory('so101_bringup')
    pkg_description = get_package_share_directory('so101_description')
    pkg_control = get_package_share_directory('so101_control')
    
    
    # real leader robot bringup node (without control only joint states)
    leader_robot_bringup_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_bringup, "launch", "real_leader.launch.py")),
    )
    
    # sim follower robot bringup node (with trajectory control)
    follower_robot_bringup_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_bringup, "launch", "follower_gazebo_with_trajectory_control.launch.py")),
    )
    

    #####################
    # LaunchDescription
    #####################
    return LaunchDescription([
        leader_robot_bringup_node,
        follower_robot_bringup_node,

    ])
