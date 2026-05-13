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
    follower_usb_port = LaunchConfiguration('follower_usb_port', default='/dev/lerobot_follower')
    follower_joint_config_file = LaunchConfiguration('follower_joint_config_file', default='')
    follower_gazebo_controllers_config = LaunchConfiguration(
        'follower_gazebo_controllers_config',
        default=os.path.join(pkg_control, 'config', 'so101_follower_controllers.yaml'),
    )

    #####################
    # Robot descriptions
    #####################
    with open(scene_urdf_path, 'r') as f:
        scene_description = f.read()

    follower_description = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ', arm_xacro_path,
        ' sim_mode:=', sim_mode,
        ' arm_prefix:=follower',
        ' usb_port:=', follower_usb_port,
        ' joint_config_file:=', follower_joint_config_file,
        ' gazebo_controllers_config:=', follower_gazebo_controllers_config,
    ])

    # Leader: description only — ros2_control block skipped via moveit_status:=true
    leader_description = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ', arm_xacro_path,
        ' sim_mode:=', sim_mode,
        ' moveit_status:=true',
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

    # Physical placement: attach each arm's base_link to table_link.
    # Follower is on the LEFT (+Y) from the operator's view.
    # Leader is on the RIGHT (-Y), 0.5 m from follower.
    static_tf_follower = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_follower_base',
        # args: x  y     z     yaw pitch roll  parent        child
        arguments=['0', '0.25', '0.47', '0', '0', '0', 'table_link', 'follower_world'],
    )

    static_tf_leader = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_leader_base',
        arguments=['0', '-0.25', '0.47', '0', '0', '0', 'table_link', 'leader/base_link'],
    )

    #####################
    # Follower arm description  (/follower/ namespace)
    #####################
    follower_description_group = GroupAction([
        PushRosNamespace('follower'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': ParameterValue(follower_description, value_type=str),
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
            'follower_usb_port',
            default_value='/dev/lerobot_follower',
            description='Serial port for the follower arm',
        ),
        DeclareLaunchArgument(
            'follower_joint_config_file',
            default_value='',
            description='Absolute path to follower calibration YAML (homing_offset, range_min, range_max)',
        ),
        DeclareLaunchArgument(
            'follower_gazebo_controllers_config',
            default_value=os.path.join(
                get_package_share_directory('so101_control'), 'config', 'so101_follower_controllers.yaml'
            ),
            description='Absolute path to the Gazebo controllers YAML for the follower arm',
        ),

        scene_state_publisher,
        static_tf_follower,
        # static_tf_leader,
        follower_description_group,
        # leader_description_group,
    ])
