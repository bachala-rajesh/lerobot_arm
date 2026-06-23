#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:

    pkg_description = get_package_share_directory('so101_description')

    scene_urdf_path = os.path.join(pkg_description, 'urdf', 'scene.urdf')
    arm_xacro_path = os.path.join(pkg_description, 'urdf', 'so101_arm_with_control.urdf.xacro')

    #####################
    # Launch args
    #####################

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    sim_mode = LaunchConfiguration('sim_mode', default='real_robot')
    dof_type = LaunchConfiguration('dof_type', default='dof_5')
    follower_usb_port = LaunchConfiguration('follower_usb_port', default='/dev/lerobot_follower')
    follower_joint_config_file = LaunchConfiguration('follower_joint_config_file', default='')

    # Select the correct controllers YAML based on dof_type (used for Gazebo sim_mode only)
    controllers_yaml_filename = PythonExpression([
        "'so101_follower_6dof_controllers.yaml' if '", dof_type, "' == 'dof_6' else 'so101_follower_controllers.yaml'"
    ])
    gazebo_controllers_yaml = PathJoinSubstitution([
        FindPackageShare('so101_control'), 'config', controllers_yaml_filename
    ])

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
        ' dof_type:=', dof_type,
        ' usb_port:=', follower_usb_port,
        ' joint_config_file:=', follower_joint_config_file,
        ' gazebo_controllers_config:=', gazebo_controllers_yaml,
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

    # Physical placement: attach each arm's base_link to world.
    # Follower is on the LEFT (+Y) from the operator's view.
    # Leader is on the RIGHT (-Y), 0.5 m from follower.
    # NOTE: world -> follower_base_link is published by the URDF world_joint
    # (via the arm's robot_state_publisher) in ALL modes. A separate
    # static_transform_publisher here would DUPLICATE/conflict with it, so it was
    # removed. If a real-robot mount offset is ever needed, set it in the URDF
    # world_joint (single source), not a separate node.

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
            'dof_type',
            default_value='dof_5',
            description='Arm variant: dof_5 (default) or dof_6 (6DOF wrist_yaw)',
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

        scene_state_publisher,
        # static_tf_follower removed — world_joint (URDF) is the single source.
        follower_description_group,
        # leader_description_group,
    ])
