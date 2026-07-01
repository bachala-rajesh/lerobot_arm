#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description() -> LaunchDescription:

    #####################
    # Paths
    #####################
    pkg_bringup = get_package_share_directory('so101_bringup')
    pkg_description = get_package_share_directory('so101_description')
    pkg_control = get_package_share_directory('so101_control')

    controllers_yaml = os.path.join(pkg_control, 'config', 'so101_controllers.yaml')
    follower_calibration = os.path.join(pkg_bringup, 'config', 'so101_follower_calibration.yaml')
    description_launch_path = os.path.join(pkg_description, 'launch', 'follower_description.launch.py')
    

    #####################
    # Launch args
    #####################
    sim_mode = LaunchConfiguration("sim_mode", default="real_robot")
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    dof = LaunchConfiguration('dof', default='5')
    follower_usb_port = LaunchConfiguration('follower_usb_port', default='/dev/lerobot_follower')

    #####################
    # Description (scene + both arm RSPs + static TFs)
    #####################
    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(description_launch_path),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'sim_mode': 'real_robot',
            'dof': dof,
            'follower_usb_port': follower_usb_port,
            'follower_joint_config_file': follower_calibration,
        }.items(),
    )


    #control node
    control_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_control, "launch", "follower_joints_trajectory_control.launch.py")),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "sim_mode": sim_mode,
            "dof": dof,
        }.items(),
    )


    #####################
    # LaunchDescription
    #####################
    return LaunchDescription([
        DeclareLaunchArgument(
            'dof',
            default_value='5',
            description='Follower arm variant: 5 or 6',
        ),
        DeclareLaunchArgument(
            'follower_usb_port',
            default_value='/dev/lerobot_follower',
            description='Serial port for the follower arm',
        ),

        description_launch,
        control_node,   
    ])
