from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # get path of config file
    oak_config_yaml = PathJoinSubstitution(
        [FindPackageShare("image_pipeline"), "config", "test_oakd_camera_params.yaml"]
    )

    container = ComposableNodeContainer(
        name="oakd_container",
        namespace="",
        package="rclcpp_components",
        executable="component_container",
        composable_node_descriptions=[
            # node for depthai_ros
            ComposableNode(
                package="depthai_ros_driver",
                plugin="depthai_ros_driver::Camera",
                name="oak",
                parameters=[
                    oak_config_yaml,
                ],
            ),
            # formatting the left image
            # ComposableNode(
            #     package="isaac_ros_image_proc",
            #     plugin="nvidia::isaac_ros::image_proc::ImageFormatConverterNode",
            #     name="left_converter_node",
            #     remappings=[
            #         ("image_raw", "/oak/left/image_raw"),
            #         ("image", "/oak/left/image_converted"),
            #     ],
            # ),
            # # node for isaac ros rectify node for left camera
            # ComposableNode(
            #     package="isaac_ros_image_proc",
            #     plugin="nvidia::isaac_ros::image_proc::RectifyNode",
            #     name="left_rectify_node",
            #     remappings=[
            #         ("image_raw", "/oak/left/image_converted"),
            #         ("camera_info", "/oak/left/camera_info"),
            #         ("image_rect", "/oak/left/image_rect"),
            #     ],
            # ),
            # formatting the right image
            # ComposableNode(
            #     package="isaac_ros_image_proc",
            #     plugin="nvidia::isaac_ros::image_proc::ImageFormatConverterNode",
            #     name="right_converter_node",
            #     remappings=[
            #         ("image_raw", "/oak/right/image_raw"),
            #         ("image", "/oak/right/image_converted"),
            #     ],
            # ),
            # # node for isaac ros rectify node for right camera
            # ComposableNode(
            #     package="isaac_ros_image_proc",
            #     plugin="nvidia::isaac_ros::image_proc::RectifyNode",
            #     name="right_rectify_node",
            #     remappings=[
            #         ("image_raw", "/oak/right/image_converted"),
            #         ("camera_info", "/oak/right/camera_info"),
            #         ("image_rect", "/oak/right/image_rect"),
            #     ],
            # ),
            # node for stereo
            ComposableNode(
                package="isaac_ros_stereo_image_proc",
                plugin="nvidia::isaac_ros::stereo_image_proc::DisparityNode",
                name="disparity_node",
                remappings=[
                    ("left/image_rect", "/oak/left/image_rect"),
                    ("right/image_rect", "/oak/right/image_rect"),
                    ("left/camera_info", "/oak/left/camera_info"),
                    ("right/camera_info", "/oak/right/camera_info"),
                ],
            ),
        ],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription([container])
