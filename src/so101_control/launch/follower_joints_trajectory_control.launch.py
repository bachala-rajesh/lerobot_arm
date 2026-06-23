import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, TimerAction
from launch.substitutions import LaunchConfiguration, PythonExpression
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():

    pkg_control = get_package_share_directory('so101_control')
    controllers_yaml_5dof = os.path.join(pkg_control, 'config', 'so101_follower_controllers.yaml')
    controllers_yaml_6dof = os.path.join(pkg_control, 'config', 'so101_follower_6dof_controllers.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    sim_mode = LaunchConfiguration('sim_mode', default='real_robot')
    dof_type = LaunchConfiguration('dof_type', default='dof_5')

    controllers_yaml = PythonExpression([
        "'", controllers_yaml_6dof, "' if '", dof_type, "' == 'dof_6' else '", controllers_yaml_5dof, "'"
    ])

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
            arguments=['arm_controller',
                       '--controller-manager', '/follower/controller_manager'],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
            emulate_tty=True,
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['gripper_controller',
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
        DeclareLaunchArgument(
            'dof_type',
            default_value='dof_5',
            description='Follower arm variant: dof_5 or dof_6',
        ),

        controller_manager_group,
        TimerAction(period=3.0, actions=controller_spawners),
    ])
