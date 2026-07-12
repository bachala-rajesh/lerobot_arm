import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('moveit_commander'),
        'config',
        'moveit_commander_params.yaml',
    )

    return LaunchDescription([
        Node(
            package="moveit_commander",
            executable="commander_5dof",
            name="commander_5dof",
            namespace="follower",
            output="screen",
            parameters=[config],
        ),
    ])
