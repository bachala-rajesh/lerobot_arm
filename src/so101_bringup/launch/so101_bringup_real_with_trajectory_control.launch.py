#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition


def generate_launch_description() -> LaunchDescription:
   
    ##################### 
    # packages path
    #####################
    pkg_bringup = get_package_share_directory("so101_bringup")
    pkg_control = get_package_share_directory("so101_control")
    pkg_robot_description = get_package_share_directory("so101_follower_description")
   
    
    ##################### 
    # launch arguments and configurations related 
    #####################
    use_sim_time = LaunchConfiguration("use_sim_time", default="false")
    sim_mode = LaunchConfiguration("sim_mode", default="real_robot")



    #####################
    # Nodes 
    #####################
    # robot description node
    robot_description_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_robot_description, "launch", "so101_follower_description.launch.py")),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "sim_mode": sim_mode,
        }.items(),
    )
    
    # real robot bringup node
    real_robot_bringup_node = Node(
        package="so101_bringup",
        executable="motor_bridge.py",
        name="real_robot_bringup",
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
        ],
        emulate_tty=True,
    )
    
    
    #control node
    control_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_control, "launch", "joints_trajectory_control.launch.py")),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "sim_mode": sim_mode,
        }.items(),
    ) 


    #####################
    # creating LaunchDescription
    #####################
    
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation (Gazebo) clock if true",
            ),
            DeclareLaunchArgument(
                "sim_mode",
                default_value="real_robot",
                description="Simulation mode: gazebo or isaacsim or real_robot",
            ),
            
            robot_description_node,
            real_robot_bringup_node,
            control_node,
        ]
    )
