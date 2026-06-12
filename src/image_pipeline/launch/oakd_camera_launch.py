import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, PushRosNamespace
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    use_sim_time = LaunchConfiguration("use_sim_time", default="false")
    camera_model = LaunchConfiguration("camera_model", default="OAK-D")

    # ----- OAK-D URDF (publishes static TFs for all camera frames) -----
    urdf_launch_path = os.path.join(
        get_package_share_directory("depthai_descriptions"),
        "launch",
        "urdf_launch.py",
    )
    # Wrap in a namespace so this robot_state_publisher publishes
    # /oak/robot_description (not /robot_description) — avoids clash
    # with the main robot's robot_state_publisher.
    urdf_launch = GroupAction(
        actions=[
            PushRosNamespace("oak"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(urdf_launch_path),
                launch_arguments={
                    "camera_model": camera_model,
                    "tf_prefix": "oak",
                    "use_sim_time": use_sim_time,
                }.items(),
            ),
        ]
    )

    # ----- OAK-D driver (RGB / depth / IMU streams) -----
    oak_config_yaml = PathJoinSubstitution(
        [FindPackageShare("image_pipeline"), "config", "oakd_camera_params.yaml"]
    )

    container = ComposableNodeContainer(
        name="oakd_container",
        namespace="",
        package="rclcpp_components",
        executable="component_container",
        composable_node_descriptions=[
            ComposableNode(
                package="depthai_ros_driver",
                plugin="depthai_ros_driver::Camera",
                name="oak",
                parameters=[
                    oak_config_yaml,
                    {"use_sim_time": use_sim_time},
                ],
            )
        ],
        output="screen",
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
            urdf_launch,
            container,
        ]
    )
