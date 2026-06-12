from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os
from ament_index_python.packages import get_package_share_directory
import xacro


def generate_launch_description():
    # Check if we're told to use sim time
    use_sim_time = LaunchConfiguration("use_sim_time")

    # New parameter to control whether to show GUI sliders or use real robot
    use_gui = LaunchConfiguration("use_gui")

    # Parameter for which joint_states topic to use
    joint_states_topic = LaunchConfiguration("joint_states_topic")

    # Process the URDF file
    pkg_path = os.path.join(get_package_share_directory("so101_description"))
    xacro_file = os.path.join(pkg_path, "urdf", "robots", "so101_arm.urdf.xacro")
    robot_description_config = xacro.process_file(xacro_file)
    robot_description = {"robot_description": robot_description_config.toxml()}

    # Create a robot_state_publisher node
    node_robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
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
