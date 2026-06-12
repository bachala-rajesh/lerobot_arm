import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    pkg_name = 'yolo2cloud'
    object_detection_params_file = os.path.join(get_package_share_directory(pkg_name),
                                            'config',
                                            'yolo_object_detection_params.yaml',
                                        )
    
    object_detection_node = Node(
                                package=pkg_name,
                                executable='run_yolo_obj_bboxes3d.py',
                                name='run_yolo_obj_bboxes3d_node',
                                parameters=[object_detection_params_file],
                                output="screen",
                                emulate_tty=True,
                            )

                        

    return LaunchDescription([
        object_detection_node
    ])
