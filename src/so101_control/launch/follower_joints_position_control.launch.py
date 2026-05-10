import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, TimerAction
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.conditions import IfCondition
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():

    controllers_yaml = os.path.join(
        get_package_share_directory('so101_control'),
        'config',
        'so101_follower_controllers.yaml',
    )

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    sim_mode = LaunchConfiguration('sim_mode', default='real_robot')

    # ros2_control_node — skipped in Gazebo (Gazebo spawns its own via the URDF plugin)
    controller_manager_group = GroupAction(
        condition=IfCondition(
            PythonExpression(["'", sim_mode, "' != 'gazebo'"])
        ),
        actions=[
            PushRosNamespace('follower'),
            Node(
                package='controller_manager',
                executable='ros2_control_node',
                parameters=[
                    controllers_yaml,
                    {'use_sim_time': use_sim_time},
                ],
                remappings=[
                    ('~/robot_description', 'robot_description'),
                ],
                output='screen',
                emulate_tty=True,
            ),
        ],
    )

    controller_spawners = [
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joint_state_broadcaster',
                       '--controller-manager', '/follower/controller_manager'],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
            emulate_tty=True,
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joints_position_controller',
                       '--controller-manager', '/follower/controller_manager'],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
            emulate_tty=True,
        ),
    ]

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'sim_mode',
            default_value='real_robot',
            description='Hardware mode: real_robot, gazebo, or isaacsim',
        ),

        controller_manager_group,
        TimerAction(period=5.0, actions=controller_spawners),
    ])
