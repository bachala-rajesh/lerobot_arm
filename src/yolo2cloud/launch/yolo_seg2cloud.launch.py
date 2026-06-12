import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    pkg_name = 'yolo2cloud'
    segmentation_params_file = os.path.join(get_package_share_directory(pkg_name),
                                            'config',
                                            'yolo_seg2cloud_params.yaml',
                                        )
    
    segmentation_node = Node(
                                package=pkg_name,
                                executable='yolo_seg2cloud.py',
                                name='yolo_seg2cloud_node',
                                parameters=[segmentation_params_file],
                                remappings=[("/image", "/oak/rgb/image_raw"),
                                            ("/depth_image", "/oak/stereo/image_raw"),
                                            ("/camera_info", "/oak/rgb/camera_info")],
                                output="screen",
                                emulate_tty=True,
                            )

    return LaunchDescription([
        segmentation_node
    ])
