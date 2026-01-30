import os
import yaml
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch.actions import ExecuteProcess
import xacro
from moveit_configs_utils import MoveItConfigsBuilder
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def load_file(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    
    try:
        with open(absolute_file_path, "r") as file:
            return file.read()
    except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
        return None


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    try:
        with open(absolute_file_path, "r") as file:
            return yaml.safe_load(file)
    except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
        return None


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    
    moveit_config = (
        MoveItConfigsBuilder("so101")
        .robot_description(file_path="config/so101_follower.urdf.xacro")
        .joint_limits(file_path="config/joint_limits.yaml")
        .robot_description_kinematics()
        .to_moveit_configs()
    )

    # Get parameters for the Servo node
    servo_yaml = load_yaml("so101_moveit_servo", "config/servo_config_forward_command_controller.yaml")
    servo_params = {"moveit_servo": servo_yaml}
    # servo_params = servo_yaml


    acceleration_filter_update_period = {"update_period": 0.01}
    planning_group_name = {"planning_group_name": "arm"}


    # RViz
    rviz_config_file = (
        get_package_share_directory("so101_moveit_servo") + "/rviz/demo_rviz_config.rviz"
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            {'use_sim_time': use_sim_time},
        ],
        emulate_tty=True,
    )


    # Launch a standalone Servo node.
    # As opposed to a node component, this may be necessary (for example) if Servo is running on a different PC
    servo_node = Node(
        package="moveit_servo",
        executable="servo_node_main",
        parameters=[
            servo_params,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            acceleration_filter_update_period,
            planning_group_name,
            {'use_sim_time': use_sim_time},
        ],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'use_sim_time',
                default_value='true',
                description='Use simulation (Gazebo) clock if true'
            ),
            rviz_node,
            servo_node,
        ]
    )
