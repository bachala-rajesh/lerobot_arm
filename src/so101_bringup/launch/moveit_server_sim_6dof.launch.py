from moveit_configs_utils import MoveItConfigsBuilder

from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def generate_launch_description():

    #####################
    # package paths
    #####################
    pkg_moveit_name = "so101_6dof_moveit_config"
    pkg_bringup = get_package_share_directory("so101_bringup")

    #####################
    # launch arguments
    #####################
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    #####################
    # nodes
    #####################

    # Move Group Node
    moveit_config = MoveItConfigsBuilder(
        "so101_arm", package_name=pkg_moveit_name
    ).to_moveit_configs()

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        namespace="follower",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"trajectory_execution.allowed_execution_duration_scaling": 2.0},
            {"publish_robot_description_semantic": True},
            {"use_sim_time": use_sim_time},
            {"default_planning_pipeline": "ompl"},
        ],
        emulate_tty=True,
    )

    rviz_config = os.path.join(pkg_bringup, "rviz", "moveit.rviz")
    rviz_moveit_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config, "--ros-args", "--log-level", "WARN"],
        # Minimal params only — passing to_dict() here causes intermittent segfault in ROS2 Humble
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            {"use_sim_time": use_sim_time},
        ],
        emulate_tty=True,
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use simulation (Gazebo) clock if true",
            ),
            move_group_node,
            rviz_moveit_node,
        ]
    )
