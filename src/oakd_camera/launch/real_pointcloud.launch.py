"""
Standalone launch: starts the real OAK-D camera (real.launch.py) AND adds
point cloud nodes on top of it — nothing else needs to be launched first.

This file includes real.launch.py to start the camera + its composable node
container (name: oakd_container, also loads the rgb rectify node), then
loads depth_image_proc nodes into that SAME container instead of building
its own.

XYZ node   in : /oak/stereo/image_raw (depth, aligned to rgb frame) + /oak/rgb/camera_info
           out: /oak/points (PointCloud2, xyz — no color)
XYZRGB node in : /oak/rgb/image_rect_color + /oak/rgb/camera_info + /oak/stereo/image_raw
           out: /oak/points_rgb (PointCloud2, colored)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LoadComposableNodes
from launch_ros.descriptions import ComposableNode


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration("use_sim_time", default="false")
    camera_model = LaunchConfiguration("camera_model", default="OAK-D")

    real_launch_path = os.path.join(
        get_package_share_directory("oakd_camera"),
        "launch",
        "real.launch.py",
    )
    real_camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(real_launch_path),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "camera_model": camera_model,
        }.items(),
    )

    load_pointcloud_node = LoadComposableNodes(
        target_container="oakd_container",
        composable_node_descriptions=[
            ComposableNode(
                package="depth_image_proc",
                plugin="depth_image_proc::PointCloudXyzrgbNode",
                name="oak_pointcloud_rgb",
                remappings=[
                    ("rgb/camera_info", "/oak/rgb/camera_info"),
                    ("rgb/image_rect_color", "/oak/rgb/image_rect"),
                    ("depth_registered/image_rect", "/oak/stereo/image_raw"),
                    ("points", "/oak/points"),
                ],
            ),
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock if true",
            ),
            DeclareLaunchArgument(
                "camera_model",
                default_value="OAK-D",
                description="OAK-D variant: OAK-D, OAK-D-LITE, OAK-D-PRO, OAK-D-PRO-W, OAK-D-S2, etc.",
            ),
            real_camera_launch,
            load_pointcloud_node,
        ]
    )
