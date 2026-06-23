from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # get path of config file
    oak_config_yaml = PathJoinSubstitution(
        [FindPackageShare("oakd_camera"), "config", "test_oakd_camera_params.yaml"]
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
                parameters=[oak_config_yaml, {"pointcloud.enable": True}],
            ),
            # ComposableNode(
            #     package="depth_image_proc",
            #     plugin="depth_image_proc::RegisterNode",
            #     name="register_node",
            #     remappings=[
            #         ("rgb/camera_info", "/oak/rgb/camera_info"),
            #         ("depth/camera_info", "/oak/stereo/camera_info"),
            #         ("depth/image_rect", "/oak/stereo/image_rect"),
            #         ("depth_registered/image_rect", "/oak/depth_registered/image_rect"),
            #         ("depth_registered/camera_info", "/oak/depth_registered/camera_info"),
            #     ],
            # ),
            # ComposableNode(
            #     package="depth_image_proc",
            #     plugin="depth_image_proc::PointCloudXyzrgbNode",
            #     name="point_cloud_xyzrgb_node",
            #     remappings=[
            #         ("depth_registered/image_rect", "/oak/depth_registered/image_rect"),
            #         ("rgb/image_rect_color", "/oak/rgb/image_rect"),
            #         ("rgb/camera_info", "/oak/rgb/camera_info"),
            #         ("points", "/oak/points"),
            #     ],
            # ),
        ],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription([container])
