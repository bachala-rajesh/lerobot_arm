"""
Build the OAK-D point cloud in ROS from the (sim) depth image — SIM only.

Why: bridging the gz point cloud (PointCloudPacked) is slow. Instead we bridge
only the light depth IMAGE, and build the cloud here with depth_image_proc. This
is faster AND mirrors the real OAK-D pipeline (real also builds the cloud from
depth, see oakd_camera_with_pointclouds.launch.py).

Input  : /oak/stereo/image_raw (32FC1, metres — gz depth) + /oak/stereo/camera_info
Output : /oak/points (PointCloud2, xyz)

The cloud frame_id = depth image frame_id = the gz scoped sensor name. A static
TF (in follower_gazebo.launch.py) connects that frame to the TF tree.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    container = ComposableNodeContainer(
        name="oak_pointcloud_container",
        namespace="",
        package="rclcpp_components",
        executable="component_container",
        composable_node_descriptions=[
            ComposableNode(
                package="depth_image_proc",
                plugin="depth_image_proc::PointCloudXyzNode",
                name="oak_pointcloud_xyz",
                parameters=[{"use_sim_time": use_sim_time}],
                remappings=[
                    ("image_rect", "/oak/stereo/image_raw"),   # 32FC1 depth (m)
                    ("camera_info", "/oak/stereo/camera_info"),
                    ("points", "/oak/points"),
                ],
            ),
        ],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use Gazebo simulation clock",
            ),
            container,
        ]
    )
