from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # get path of config file
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
                ],
                remappings=[
                    ("/oak/imu/data", "/imu/data"),  # remapping of imu topic from oakd
                ],
            )
        ],
        output="screen",
    )

    return LaunchDescription([container])
