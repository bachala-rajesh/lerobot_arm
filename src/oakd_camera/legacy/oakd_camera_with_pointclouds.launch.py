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
            # node for to bringup oakd camera
            ComposableNode(
                package="depthai_ros_driver",
                plugin="depthai_ros_driver::Camera",
                name="oak",
                parameters=[
                    oak_config_yaml,
                ],
            ),
            # node for to convert 16UC1 encoding to 32FC1, including conversion of millimeters to meters
            ComposableNode(
                package="isaac_ros_depth_image_proc",
                plugin="nvidia::isaac_ros::depth_image_proc::ConvertMetricNode",
                name="convert_metric",
                remappings=[
                    ("image_raw", "/oak/stereo/image_raw"),  # 16UC1 mm in
                    ("image", "/oak/depth/image_metric"),  # 32FC1 m out
                ],
            ),
            # changing the encoding of the rgb image from bgr8 to rgb8
            ComposableNode(
                package="isaac_ros_image_proc",
                plugin="nvidia::isaac_ros::image_proc::ImageFormatConverterNode",
                name="image_format_converter",
                parameters=[{"encoding_desired": "rgb8"}],
                remappings=[
                    ("image_raw", "/oak/rgb/image_raw"),  # BGR8 input
                    ("image", "/oak/rgb/image_rgb8"),  # RGB8 output
                ],
            ),
            # node for processing depth to point clouds
            ComposableNode(
                package="isaac_ros_depth_image_proc",
                plugin="nvidia::isaac_ros::depth_image_proc::PointCloudXyzrgbNode",
                name="pointcloud_node",
                parameters=[
                    {"skip": 4}  # Only every 2nd pixel is converted to a point
                ],
                remappings=[
                    ("depth_registered/image_rect", "/oak/depth/image_metric"),
                    ("rgb/image_rect_color", "/oak/rgb/image_rgb8"),
                    ("rgb/camera_info", "/oak/rgb/camera_info"),
                    ("points", "/oak/points"),
                ],
            ),
            # # node for processing depth to point clouds
            # ComposableNode(
            #     package='isaac_ros_depth_image_proc',
            #     plugin='nvidia::isaac_ros::depth_image_proc::PointCloudXyzNode',
            #     name='pointcloud_node',
            #     remappings=[
            #         ('image_rect', '/oak/depth/image_metric'),
            #         ('camera_info', '/oak/rgb/camera_info'),
            #         ('points', '/oak/points')
            #     ]
            # ),
        ],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription([container])
