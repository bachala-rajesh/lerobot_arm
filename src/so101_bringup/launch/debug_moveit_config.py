from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch

from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import LaunchConfiguration
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    #####################
    # package paths
    #####################
    pkg_moveit_name = "so101_moveit_config"
    pkg_bringup = get_package_share_directory("so101_bringup")
    pkg_moveit = get_package_share_directory(pkg_moveit_name)

    #####################
    # launch arguments and configurations related
    #####################
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    #####################
    # nodes
    #####################

    # Move Group Node
    moveit_config = MoveItConfigsBuilder(
        "so101_arm", package_name=pkg_moveit_name
    ).to_moveit_configs()

    # debugging
    moveit_dict = moveit_config.to_dict()
    for item, value in moveit_dict.items():
        print(f"{item}: {value}")
        print("-----------------")

    return LaunchDescription([])
