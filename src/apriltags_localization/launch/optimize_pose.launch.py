from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # get the pkg path of the apriltags config file:
    pkg_path = get_package_share_directory("apriltags_localization")
    apriltag_config_path = os.path.join(pkg_path, "config", "sim_apriltags_detections_config.yaml")
    global_location_config_path = os.path.join(pkg_path, "config", "optimize_pose_config.yaml")

    apriltag_detection_node = Node(
        package="apriltag_ros",
        executable="apriltag_node",
        name="apriltag_detection_node",
        output="screen",
        parameters=[apriltag_config_path],
        remappings=[
            ("/image_rect", "/oak/rgb/image_raw"),
            ("/camera_info", "/oak/rgb/camera_info"),
            ("/detections", "/detections_apriltags"),
        ],
        emulate_tty=True,
    )

    optimize_pose_node = Node(
        package="apriltags_localization",
        executable="optimize_pose.py",
        name="optimize_pose_node",
        output="screen",
        parameters=[global_location_config_path],
        remappings=[("/camera_info", "/oak/rgb/camera_info"), ("/detections", "/detections_apriltags")],
        emulate_tty=True,
    )

    # Create and return LaunchDescription
    return LaunchDescription([apriltag_detection_node, optimize_pose_node])
