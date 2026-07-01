#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
   
    #####################
    # get packages path 
    #####################
    pkg_bringup = get_package_share_directory("so101_bringup")
    pkg_robot_description = get_package_share_directory("so101_description")
    
    so101_description_share_path = os.path.dirname(pkg_robot_description)
    
    # Set GAZEBO resource path to include biped_description package
    set_gazebo_resource_path = AppendEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=so101_description_share_path
    )
    
    
    
    ##################### 
    # launch arguments and configurations related 
    #####################
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    dof = LaunchConfiguration("dof", default="5")
    use_camera = LaunchConfiguration("use_camera", default="true")

    pkg_oakd_camera = get_package_share_directory("oakd_camera")

    # OAK-D camera mount pose (world -> camera). This is the SINGLE place to set
    # where the sim camera sits. Edit here, or override on the CLI, e.g.
    #   cam_pos_x:=0.5 cam_pitch:=0.7
    # xyz in metres, rpy in radians.
    cam_pose = {
        "cam_pos_x": LaunchConfiguration("cam_pos_x", default="0.4"),
        "cam_pos_y": LaunchConfiguration("cam_pos_y", default="0.0"),
        "cam_pos_z": LaunchConfiguration("cam_pos_z", default="1.5"),
        "cam_roll": LaunchConfiguration("cam_roll", default="0.0"),
        "cam_pitch": LaunchConfiguration("cam_pitch", default="0.6"),
        "cam_yaw": LaunchConfiguration("cam_yaw", default="3.14159"),
    }

    #####################
    # Nodes
    #####################

    # robot description node
    robot_description_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_robot_description, "launch", "follower_description.launch.py")),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "sim_mode": "gazebo",
            "dof": dof,
        }.items(),
    )
    
    # gazebo world node
    world_path = os.path.join(
        pkg_bringup,
        "world",
        "ignition_worlds",
        "robot_arm_world.sdf",
    )
    world_sdf = LaunchConfiguration("world_sdf", default=world_path)
    gz_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={
            # -r = run immediately, -v4 = verbose, then the world file name
            "gz_args": ["-r ", world_sdf],
        }.items(),
    )

    # Start ros_gz_bridge
    gazebo_bridge_config_path = PathJoinSubstitution([pkg_bringup, "config", "gz_bridge.yaml"])
    gz_bridge_node = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_bridge",
        parameters=[{"use_sim_time": use_sim_time}, {"config_file": gazebo_bridge_config_path}],
        output="screen",
        emulate_tty=True,
    )
    
    
    # Spawn scene (world + table) — reads from /robot_description published by scene_state_publisher
    spawn_scene_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "/robot_description", "-name", "scene"],
        parameters=[{"use_sim_time": use_sim_time}],
        output="screen",
    )

    # Spawn follower arm at the WORLD ORIGIN (no -x -y -z -Y).
    # The arm's world placement (on the table, incl. the 6 -90 deg yaw) comes
    # from the URDF world_joint, which is built with sim_mode:=gazebo. This keeps
    # ONE source of truth: gz body, RViz/TF and MoveIt all read that same number.
    spawn_robot_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "/follower/robot_description",
                   "-name", "follower",
                   ],
        parameters=[{"use_sim_time": use_sim_time}],
        emulate_tty=True,
        output="screen",
    )
    
    

    # OAK-D camera (sim). RSP (description + TF) from oakd_camera, spawn here.
    # Gated by use_camera (default true). Pose is baked into /oak/robot_description.
    oak_camera_rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_oakd_camera, "launch", "sim_rsp.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time, **cam_pose}.items(),
        condition=IfCondition(use_camera),
    )

    spawn_oak_camera_node = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_oak_camera",
        arguments=["-topic", "/oak/robot_description", "-name", "oak_camera"],
        parameters=[{"use_sim_time": use_sim_time}],
        output="screen",
        condition=IfCondition(use_camera),
    )

    # Build /oak/points in ROS from the depth image (faster than bridging the
    # gz cloud). oakd_camera owns this processing.
    oak_pointcloud = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_oakd_camera, "launch", "sim_pointcloud.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
        condition=IfCondition(use_camera),
    )

    #####################
    # creating LaunchDescription
    #####################

    return LaunchDescription(
        [
            set_gazebo_resource_path,

            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use simulation (Gazebo) clock if true",
            ),
            DeclareLaunchArgument(
                "dof",
                default_value="5",
                description="Follower arm variant: 5 or 6",
            ),
            DeclareLaunchArgument(
                "use_camera",
                default_value="true",
                description="Spawn the simulated OAK-D camera",
            ),

            robot_description_node,
            gz_node,
            gz_bridge_node,
            spawn_scene_node,
            spawn_robot_node,
            oak_camera_rsp,
            spawn_oak_camera_node,
            oak_pointcloud,
        ]
    )
