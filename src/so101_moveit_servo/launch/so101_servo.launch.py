#!/usr/bin/env python3
"""Launch MoveIt Servo for the SO101 follower arm.

This is a self-contained launch:
  1. Brings up the robot description (via so101_description's follower_description.launch.py).
  2. Starts /follower/controller_manager (skipped in Gazebo — Gazebo spawns its own).
  3. Spawns ONLY the servo-specific controllers: joint_state_broadcaster + servo_arm_controller.
     The regular arm_controller is *not* activated to avoid two controllers fighting
     over the same command interface.
  4. Launches the moveit_servo::ServoServer composable node inside /follower namespace.

Run after this launch:
    ros2 topic pub /follower/servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped \
        '{header: {frame_id: follower_base_link}, twist: {linear: {x: 0.05}}}' --rate 50
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import ComposableNodeContainer, Node, PushRosNamespace
from launch_ros.descriptions import ComposableNode
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description() -> LaunchDescription:

    ###########################################################################
    # Paths
    ###########################################################################
    pkg_description = get_package_share_directory('so101_description')
    pkg_control = get_package_share_directory('so101_control')
    pkg_servo = get_package_share_directory('so101_moveit_servo')

    description_launch = os.path.join(pkg_description, 'launch', 'follower_description.launch.py')
    controllers_yaml = os.path.join(pkg_control, 'config', 'so101_follower_controllers.yaml')
    servo_yaml = os.path.join(pkg_servo, 'config', 'servo_config.yaml')

    ###########################################################################
    # Launch args
    ###########################################################################
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    sim_mode = LaunchConfiguration('sim_mode', default='real_robot')
    follower_usb_port = LaunchConfiguration('follower_usb_port', default='/dev/lerobot_follower')

    ###########################################################################
    # MoveIt config — Servo needs robot_description, robot_description_semantic,
    # robot_description_kinematics, and joint_limits as parameters.
    ###########################################################################
    moveit_config = (
        MoveItConfigsBuilder('so101_arm', package_name='so101_moveit_config')
        .robot_description(file_path=os.path.join(
            pkg_description, 'urdf', 'so101_arm_with_control.urdf.xacro'))
        .to_moveit_configs()
    )

    ###########################################################################
    # Description (RSP for follower + scene + static TFs)
    ###########################################################################
    description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(description_launch),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'sim_mode': sim_mode,
            'follower_usb_port': follower_usb_port,
        }.items(),
    )

    ###########################################################################
    # ros2_control_node  (skipped in Gazebo — Gazebo plugin owns it there)
    ###########################################################################
    controller_manager = GroupAction(
        condition=IfCondition(PythonExpression(["'", sim_mode, "' != 'gazebo'"])),
        actions=[
            PushRosNamespace('follower'),
            Node(
                package='controller_manager',
                executable='ros2_control_node',
                parameters=[controllers_yaml, {'use_sim_time': use_sim_time}],
                remappings=[('~/robot_description', 'robot_description')],
                output='screen',
                emulate_tty=True,
            ),
        ],
    )

    ###########################################################################
    # Controller spawners — ONLY the servo controller; no trajectory controller.
    ###########################################################################
    controller_spawners = [
        Node(
            package='controller_manager',
            executable='spawner',
            namespace='follower',
            arguments=['joint_state_broadcaster',
                       '--controller-manager', '/follower/controller_manager'],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            namespace='follower',
            arguments=['servo_arm_controller',
                       '--controller-manager', '/follower/controller_manager'],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
        ),
    ]

    ###########################################################################
    # MoveIt Servo  (composable node, runs inside /follower namespace)
    ###########################################################################
    servo_params = {'moveit_servo': {}}
    # MoveItConfigsBuilder gives us all the description params Servo needs.
    servo_node_params = [
        servo_yaml,
        moveit_config.robot_description,
        moveit_config.robot_description_semantic,
        moveit_config.robot_description_kinematics,
        moveit_config.joint_limits,
        {'use_sim_time': use_sim_time},
    ]

    servo_container = ComposableNodeContainer(
        name='servo_container',
        namespace='follower',
        package='rclcpp_components',
        executable='component_container_mt',
        output='screen',
        composable_node_descriptions=[
            ComposableNode(
                package='moveit_servo',
                plugin='moveit_servo::ServoServer',
                name='servo_node',
                namespace='follower',
                parameters=servo_node_params,
            ),
        ],
    )

    ###########################################################################
    # LaunchDescription — order: description → controller_manager → spawners → servo
    # Use TimerAction to let the controller_manager settle before spawners/servo start.
    ###########################################################################
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('sim_mode', default_value='real_robot',
                              description='real_robot | gazebo | isaacsim'),
        DeclareLaunchArgument('follower_usb_port', default_value='/dev/lerobot_follower'),

        description,
        controller_manager,
        TimerAction(period=3.0, actions=controller_spawners),
        TimerAction(period=5.0, actions=[servo_container]),
    ])
