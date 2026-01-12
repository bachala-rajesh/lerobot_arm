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
from launch_ros.parameter_descriptions import ParameterValue
import xacro
from launch.actions import LogInfo


def generate_launch_description() -> LaunchDescription:

    ##################### 
    # Launch configurations
    ##################### 
    use_sim_time = LaunchConfiguration("use_sim_time")
    sim_mode = LaunchConfiguration('sim_mode')
    

    ##################### 
    # urdf related 
    #####################
    # Process the URDF file
    pkg_path = os.path.join(get_package_share_directory('so101_follower_description'))
    xacro_file = os.path.join(pkg_path,'urdf','arm_on_table.urdf.xacro')
    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]), 
        " ",
        xacro_file,
        " ",
        "sim_mode:=", 
        sim_mode
    ])

    #Wrap it in ParameterValue 
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }


    ##################### 
    # Nodes
    ##################### 
    # Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            robot_description,
            {'use_sim_time': use_sim_time}
            ],
        emulate_tty=True,
    )

    

 
    ############################## creating LaunchDescription
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use simulation (Gazebo) clock if true",
            ),
            
            DeclareLaunchArgument(
                'sim_mode',
                default_value='gazebo',
                description='Simulation mode: isaacsim or gazebo'
            ),
            
            # log info about sim_mode
            LogInfo(msg=['[DEBUG] sim_mode is: ', LaunchConfiguration('sim_mode')]),
            
            robot_state_publisher_node,
        ]
    )
