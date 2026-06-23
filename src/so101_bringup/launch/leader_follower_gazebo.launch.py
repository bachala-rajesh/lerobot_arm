#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
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
    dof_type = LaunchConfiguration("dof_type", default="dof_5")




    #####################
    # Nodes 
    #####################
    
    # robot description node
    robot_description_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_robot_description, "launch", "leader_follower_description.launch.py")),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "sim_mode": "gazebo",
            "dof_type": dof_type,
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

    # Spawn follower arm — reads from /follower/robot_description.
    # Position in Gazebo world = table_link position (z=0.5) + static TF offset (y=0.25, z=0.47).
    spawn_follower_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "/follower/robot_description",
                   "-name", "follower",
                   "-x", "-0.25",
                   "-y", "0.4",
                   "-z", "0.97",
                   "-Y", "0.0",
                   ],
        parameters=[{"use_sim_time": use_sim_time}],
        emulate_tty=True,
        output="screen",
    )
    
    # Spawn leader arm — delayed 5 s after follower so each model's
    # gz_ros2_control plugin fully initialises before the next one starts.
    # Both models share Gz Sim's EntityComponentManager; simultaneous
    # initialisation causes a race when both claim joints of the same name.
    spawn_leader_node = TimerAction(
        period=5.0,
        actions=[Node(
            package="ros_gz_sim",
            executable="create",
            arguments=["-topic", "/leader/robot_description",
                       "-name", "leader",
                       "-x", "0.25",
                       "-y", "0.4",
                       "-z", "0.97",
                       "-Y", "0.0",
                       ],
            parameters=[{"use_sim_time": use_sim_time}],
            emulate_tty=True,
            output="screen",
        )],
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
                "dof_type",
                default_value="dof_5",
                description="Follower arm variant: dof_5 or dof_6",
            ),

            robot_description_node,
            gz_node,
            gz_bridge_node,
            spawn_scene_node,
            spawn_follower_node,
            spawn_leader_node,
        ]
    )
