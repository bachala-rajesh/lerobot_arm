


from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    

    # get the pkg path of the apriltags config file:
    pkg_path = get_package_share_directory("apriltags_localization")
    apriltag_config_path = os.path.join(pkg_path, "config", "real_apriltags_detections_config.yaml")

    # angular calibration node
    apriltag_detection_node = Node(
        package="apriltag_ros",
        executable="apriltag_node",
        name="apriltag_detection_node",
        output="screen",
        parameters=[
            apriltag_config_path, 
            {"use_sim_time": use_sim_time},
        ],
        remappings=[("/image_rect/compressed", "/oak/rgb/image_raw/compressed"),
                    ("/camera_info", "/oak/rgb/camera_info"),
                    ("/detections", "/detections_apriltags")],
        emulate_tty=True,
    )

    # Create and return LaunchDescription
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true',
        ),
        apriltag_detection_node
        ])
