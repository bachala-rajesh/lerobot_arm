from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # get the pkg path of the apriltags config file:
    pkg_path = get_package_share_directory("apriltags_localization")
    apriltag_config_path = os.path.join(pkg_path, "config", "dt_sim_apriltag_detections_config.yaml")
    global_location_config_path = os.path.join(pkg_path, "config", "sim_apriltags_global_location.yaml")

    # Launch configuration paramter

    # angular calibration node
    apriltag_detection_node = Node(
        package="apriltags_localization",
        executable="detect_apriltags.py",
        name="detect_apriltags_node",
        output="screen",
        parameters=[{"use_sim_time": True}, apriltag_config_path],
        remappings=[
            ("/image_rect", "/oak/rgb/image_raw"),
            ("/camera_info", "/oak/rgb/camera_info"),
        ],
        emulate_tty=True,
    )

    # Create and return LaunchDescription
    return LaunchDescription([apriltag_detection_node])
