from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description() -> LaunchDescription:
    cfg = os.path.join(
        get_package_share_directory("sam2_segmentor"),
        "config",
        "sam2_segmentor.yaml",
    )

    sam2_node = Node(
        package="sam2_segmentor",
        executable="sam2_node.py",
        name="sam2_node",
        parameters=[cfg],
        output="screen",
    )

    return LaunchDescription([sam2_node])
