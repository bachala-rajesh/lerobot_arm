import os
from ament_index_python.packages import get_package_share_directory
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
from launch.actions import TimerAction
from launch.substitutions import PythonExpression



def generate_launch_description():
    
    # Path to controllers yaml
    controllers_yaml = os.path.join(
        get_package_share_directory('so101_control'),
        'config',
        'so101_controllers.yaml',
    )
    
    
    # ###############
    # Configurations
    # ###############
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    sim_mode = LaunchConfiguration('sim_mode', default='gazebo')
    

    
    
    
    # ###############
    # nodes
    # ###############
    #controller manager node
    controller_manager_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            controllers_yaml,
            {"use_sim_time": use_sim_time},
        ],
        remappings=[
            ("~/robot_description", "/robot_description")
        ],
        output="screen",
        emulate_tty=True,
        # Only launch this node if not in Gazebo sim mode. 
        # Gazebo launches its own controller manager mentioned in the urdf file.
        condition=IfCondition(
            PythonExpression(["'", sim_mode, "' != 'gazebo'"])
        )
    )

    # Spawner nodes
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        parameters=[{"use_sim_time": use_sim_time}],
        output="screen",
        # Isaacsim publishes its own joint states, so no need to spawn this broadcaster.
        condition=IfCondition(
            PythonExpression([
                "('", sim_mode, "' != 'isaacsim')"
            ])
        )
    )

    joints_position_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joints_position_controller",
            "--controller-manager",
            "/controller_manager",
            "--param-file",
            controllers_yaml,
        ],
        parameters=[{"use_sim_time": use_sim_time}],
        output="screen",
    )
    
    controller_spawners = [
        joint_state_broadcaster_spawner,
        joints_position_controller_spawner,
    ]
    
    
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        DeclareLaunchArgument(
            'sim_mode',
            default_value='gazebo',
            description='Simulation mode: gazebo or isaacsim',
        ),
        

        controller_manager_node,
        TimerAction(
            period=5.0,
            actions=controller_spawners
        ),
    ])
