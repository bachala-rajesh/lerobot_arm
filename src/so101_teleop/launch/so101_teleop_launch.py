import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument



def generate_launch_description():
    
    #################
    # Packages
    # ###############
    pkg_teleop = get_package_share_directory('so101_teleop')
    
    
    # ###############
    # Configurations 
    # ###############
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    

    #################
    # Nodes
    # ###############
    # joystick node
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        output='screen',
        parameters=[{"use_sim_time": use_sim_time}],
        emulate_tty=True,
    )
    
    
    
    # teleop_node
    teleop_config = os.path.join(
        pkg_teleop,
        'config',
        'so101_teleop_params.yaml',
    )
    teleop_node = Node(
        package='so101_teleop',
        executable='so101_teleop_node',
        name='so101_teleop_node',
        output='screen',
        parameters=[teleop_config,
                    {"use_sim_time": use_sim_time}
                    ],
        emulate_tty=True,
    )
    
    

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'
        ),
        
        joy_node,
        teleop_node,
    ])
        