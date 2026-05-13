#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:

    pkg_description = get_package_share_directory('so101_description')
    pkg_control = get_package_share_directory('so101_control')

    scene_urdf_path = os.path.join(pkg_description, 'urdf', 'scene.urdf')
    arm_xacro_path = os.path.join(pkg_description, 'urdf', 'so101_arm_with_control.urdf.xacro')

    #####################
    # Launch args
    #####################

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    sim_mode = LaunchConfiguration('sim_mode', default='real_robot')
    

    leader_usb_port = LaunchConfiguration('leader_usb_port', default='/dev/lerobot_leader')
    leader_command = LaunchConfiguration('leader_command', default='false')
    leader_joint_config_file = LaunchConfiguration('leader_joint_config_file', default='')
    leader_gazebo_controllers_config = LaunchConfiguration(
        'leader_gazebo_controllers_config',
        default=os.path.join(pkg_control, 'config', 'so101_leader_controllers.yaml'),
    )

    #####################
    # Robot descriptions
    #####################
    with open(scene_urdf_path, 'r') as f:
        scene_description = f.read()

    # Leader: description only — ros2_control block skipped via moveit_status:=true
    leader_description = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ', arm_xacro_path,
        ' sim_mode:=', sim_mode,
        ' arm_type:=leader',
        ' command:=', leader_command,
        ' usb_port:=', leader_usb_port,
        ' joint_config_file:=', leader_joint_config_file,
        ' gazebo_controllers_config:=', leader_gazebo_controllers_config,
    ])

    #####################
    # Scene nodes (no namespace)
    # Owns world and table_link TF frames.
    #####################
    scene_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='scene_state_publisher',
        parameters=[{
            'robot_description': ParameterValue(scene_description, value_type=str),
            'use_sim_time': use_sim_time,
        }],
        output='screen',
    )

    # Physical placement: attach each arm's base_link to table_link
    static_tf_leader = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_leader_base',
        arguments=['0', '-0.25', '0.47', '0', '0', '0', 'table_link', 'leader/base_link'],
    )


    #####################
    # Leader arm description  (/leader/ namespace)
    #####################
    leader_description_group = GroupAction([
        PushRosNamespace('leader'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': ParameterValue(leader_description, value_type=str),
                'frame_prefix': 'leader/',
                'use_sim_time': use_sim_time,
            }],
            remappings=[
                ('tf', '/tf'),
                ('tf_static', '/tf_static'),
            ],
            output='screen',
        ),
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
            'sim_mode',
            default_value='real_robot',
            description='Hardware mode: real_robot, gazebo, or isaacsim',
        ),
        DeclareLaunchArgument(
            'leader_usb_port',
            default_value='/dev/lerobot_leader',
            description='Serial port for the leader arm',
        ),
        DeclareLaunchArgument(
            'leader_command',
            default_value='false',
            description='Enable command interface for the leader arm',
        ),
        DeclareLaunchArgument(
            'leader_joint_config_file',
            default_value='',
            description='Absolute path to leader calibration YAML (homing_offset, range_min, range_max)',
        ),
        DeclareLaunchArgument(
            'leader_gazebo_controllers_config',
            default_value=os.path.join(
                get_package_share_directory('so101_control'), 'config', 'so101_leader_controllers.yaml'
            ),
            description='Absolute path to the Gazebo controllers YAML for the leader arm',
        ),

        scene_state_publisher,
        static_tf_leader,
        leader_description_group,
    ])
