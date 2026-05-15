import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    record_motion_config = os.path.join(
        get_package_share_directory("arm_emotions"),
        "config",
        "record_motion.yaml",
    )

    record_node = Node(
        package="arm_emotions",
        executable="record_motion.py",
        name="record_motion",
        parameters=[record_motion_config],
        output="screen",
        namespace="/follower",
        emulate_tty=True,
    )

    return LaunchDescription(
        [
            record_node,
        ]
    )
