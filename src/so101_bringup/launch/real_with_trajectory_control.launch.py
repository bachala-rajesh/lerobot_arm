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

    controllers_yaml = os.path.join(pkg_control, 'config', 'so101_controllers.yaml')
    follower_calibration = os.path.join(pkg_bringup, 'config', 'so101_follower_calibration.yaml')
    description_launch_path = os.path.join(pkg_description, 'launch', 'so101_description.launch.py')

    #####################
    # Launch args
    #####################
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    follower_usb_port = LaunchConfiguration('follower_usb_port', default='/dev/lerobot_follower')

    #####################
    # Description (scene + both arm RSPs + static TFs)
    #####################
    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(description_launch_path),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'sim_mode': 'real_robot',
            'follower_usb_port': follower_usb_port,
            'follower_joint_config_file': follower_calibration,
        }.items(),
    )

    #####################
    # Follower arm control  (/follower/ namespace)
    # controller_manager loads the feetech driver and manages controllers.
    # ~/robot_description is remapped to robot_description so it reads
    # from /follower/robot_description (published by the namespaced RSP).
    #####################
    follower_spawners = [
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joint_state_broadcaster',
                       '--controller-manager', '/follower/controller_manager'],
            output='screen',
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['arm_controller',
                       '--controller-manager', '/follower/controller_manager'],
            output='screen',
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['gripper_controller',
                       '--controller-manager', '/follower/controller_manager'],
            output='screen',
        ),
    ]

    follower_control_group = GroupAction([
        PushRosNamespace('follower'),
        Node(
            package='controller_manager',
            executable='ros2_control_node',
            parameters=[controllers_yaml, {'use_sim_time': use_sim_time}],
            remappings=[('~/robot_description', 'robot_description')],
            output='screen',
        ),
        # Wait 3 s for the controller manager to initialise before spawning
        TimerAction(period=3.0, actions=follower_spawners),
    ])

    #####################
    # LaunchDescription
    #####################
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'follower_usb_port',
            default_value='/dev/lerobot_follower',
            description='Serial port for the follower arm',
        ),

        description_launch,
        follower_control_group,
    ])
