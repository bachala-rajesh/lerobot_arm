#!/usr/bin/env python3

"""
Follower arm description with NO command interfaces — servos stay backdrivable.

Why this exists
---------------
feetech_ros2_driver.cpp:210 enables servo torque only for joints that have a
<command_interface>:

    if (!joint.command_interfaces.empty()) { set_torque(id, true); }

That runs in on_init(), i.e. when the hardware loads — BEFORE any controller is
spawned. So dropping the controllers from a launch file does NOT free the arm.
The only way to keep the servos free is to publish a robot_description with no
command interfaces at all, via the xacro's command:=false.

This is the same mechanism leader_description.launch.py already uses to keep the
leader arm backdrivable — same driver, same xacro, one arg.

Use for read-only work: hand-move the arm and watch /follower/joint_states.
For anything that must COMMAND the arm, use follower_description.launch.py.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:

    pkg_description = get_package_share_directory('so101_description')
    arm_xacro_path = os.path.join(pkg_description, 'urdf', 'so101_arm_with_control.urdf.xacro')

    dof = LaunchConfiguration('dof')
    follower_usb_port = LaunchConfiguration('follower_usb_port')

    # ponytail: sim_mode/use_sim_time are not args — a torque-free rig is real-robot-only.
    # Gazebo has no servos to free, so there is nothing to configure here.
    #
    # NOTE: no calibration YAML is passed. The driver writes homing_offset AND
    # range_min/range_max straight to servo EEPROM (feetech_ros2_driver.cpp:161-189),
    # and this launch is meant to be read-only. Keep it that way.
    follower_description = Command([
        FindExecutable(name='xacro'), ' ', arm_xacro_path,
        ' sim_mode:=real_robot',
        ' arm_prefix:=follower',
        ' dof:=', dof,
        ' usb_port:=', follower_usb_port,
        ' command:=false',          # <-- the whole point of this file
    ])

    follower_description_group = GroupAction([
        PushRosNamespace('follower'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': ParameterValue(follower_description, value_type=str),
                'use_sim_time': False,
            }],
            remappings=[
                ('tf', '/tf'),
                ('tf_static', '/tf_static'),
            ],
            output='screen',
        ),
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'dof',
            default_value='5',
            description='Arm variant: 5 (default) or 6 (6DOF wrist_yaw)',
        ),
        DeclareLaunchArgument(
            'follower_usb_port',
            default_value='/dev/lerobot_follower',
            description='Serial port for the follower arm',
        ),

        # ponytail: no scene_state_publisher — the table is not needed to read joint
        # angles, and world -> follower_base_link already comes from the URDF world_joint.
        follower_description_group,
    ])
