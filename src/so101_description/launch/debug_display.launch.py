from launch import LaunchDescription
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_gui = LaunchConfiguration("use_gui")
    joint_states_topic = LaunchConfiguration("joint_states_topic")
    dof = LaunchConfiguration("dof")

    pkg_path = os.path.join(get_package_share_directory("so101_description"))
    xacro_file = os.path.join(pkg_path, "urdf", "so101_arm_with_control.urdf.xacro")

    robot_description = ParameterValue(
        Command([
            PathJoinSubstitution([FindExecutable(name='xacro')]),
            ' ', xacro_file,
            ' arm_prefix:=follower',
            ' moveit_status:=true',
            ' dof:=', dof,
        ]),
        value_type=str,
    )

    # Create a robot_state_publisher node
    node_robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{'robot_description': robot_description, 'use_sim_time': use_sim_time}],
        remappings=[("/joint_states", joint_states_topic)],
    )

    # GUI sliders (only when use_gui=true)
    joint_state_publisher_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        condition=IfCondition(use_gui),
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("so101_description"), "rviz", "display.rviz"]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
    )

    # Static TF: world -> follower_base_link (identity, for testing)
    world_to_follower_base = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="world_to_follower_base",
        arguments=[
            "--x", "0.0",
            "--y", "0.0",
            "--z", "0.0",
            "--roll", "0.0",
            "--pitch", "0.0",
            "--yaw", "0.0",
            "--frame-id", "world",
            "--child-frame-id", "follower_base_link",
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # Launch!
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use sim time if true",
            ),
            DeclareLaunchArgument(
                "dof",
                default_value="5",
                description="Arm variant: 5 (default) or 6 (6DOF wrist_yaw)",
            ),
            DeclareLaunchArgument(
                "use_gui",
                default_value="true",
                description="Whether to show joint_state_publisher_gui sliders",
            ),
            DeclareLaunchArgument(
                "joint_states_topic",
                default_value="/joint_states",
                description="Topic to get joint states from",
            ),
            node_robot_state_publisher,
            joint_state_publisher_gui,
            rviz_node,
            world_to_follower_base,
        ]
    )
