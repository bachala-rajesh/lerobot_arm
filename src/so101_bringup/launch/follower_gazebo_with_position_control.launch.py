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
   
    
    ##################### 
    # launch arguments and configurations related 
    #####################
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    sim_mode = LaunchConfiguration("sim_mode", default="gazebo")



    #####################
    # Nodes 
    #####################
    
    # simulation robot bringup node
    sim_robot_bringup_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_bringup, "launch", "follower_gazebo.launch.py")),
    )
    
    #control node
    control_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_control, "launch", "follower_joints_position_control.launch.py")),
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
                default_value="true",
                description="Use simulation (Gazebo) clock if true",
            ),
            DeclareLaunchArgument(
                "sim_mode",
                default_value="gazebo",
                description="Simulation mode: gazebo or isaacsim",
            ),
            
            sim_robot_bringup_node,
            control_node,
        ]
    )
