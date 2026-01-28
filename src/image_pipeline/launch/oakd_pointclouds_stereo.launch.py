
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution




def generate_launch_description() -> LaunchDescription:
    oak_camera_launch_include = IncludeLaunchDescription(
                                    PythonLaunchDescriptionSource([
                                        PathJoinSubstitution([
                                            FindPackageShare('depthai_ros_driver'),
                                            'launch',
                                            'camera.launch.py',
                                        ])
                                    ]),
                                    launch_arguments={
                                        'pointcloud.enable': 'true',
                                    }.items()
                                )
    
    # Start RViz
    rviz_node = Node(
                    package="rviz2",
                    executable="rviz2",
                    arguments=[
                        "-d",
                        PathJoinSubstitution(
                            [FindPackageShare("image_pipeline"), "rviz", "view_pointclouds_stereo.rviz"]
                        ),
                    ],
                    # parameters=[{'transform_tolerance': 1.0}],
                    parameters=[{"use_sim_time": False}],
                    output="screen",
                    emulate_tty=True,
                )


    return LaunchDescription(
            [
                oak_camera_launch_include,
                rviz_node
            ]
        )