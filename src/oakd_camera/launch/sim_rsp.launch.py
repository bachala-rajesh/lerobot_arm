"""
OAK-D camera robot_state_publisher — SIM (gz).

Reusable, POSE-FREE. The caller (e.g. so101_bringup/follower_gazebo.launch.py)
decides the camera pose and passes it in as launch arguments. This launch only:
  - runs xacro with the given pose
  - publishes /oak/robot_description
  - publishes world -> oak_camera_link -> oak_rgb_camera_optical_frame on /tf

Pose travels inside the description, so the spawn side (ros_gz_sim create) stays
dumb: create -topic /oak/robot_description.

cam_pos_* / cam_roll / cam_pitch / cam_yaw are REQUIRED (no defaults here) — the
caller must provide them. Not meant to run standalone.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

# Camera mount pose args (world -> camera). Values come from the caller.
POSE_ARGS = ["cam_pos_x", "cam_pos_y", "cam_pos_z", "cam_roll", "cam_pitch", "cam_yaw"]


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    xacro_file = PathJoinSubstitution(
        [FindPackageShare("oakd_camera"), "urdf", "oakd_camera_sim.urdf.xacro"]
    )

    # Build: xacro <file> cam_pos_x:=<val> ...  (values forwarded from caller)
    xacro_cmd = ["xacro ", xacro_file]
    for name in POSE_ARGS:
        xacro_cmd += [" ", name, ":=", LaunchConfiguration(name)]
    robot_description = ParameterValue(Command(xacro_cmd), value_type=str)

    # RSP namespaced "oak" -> /oak/robot_description; publishes TF on /tf.
    camera_state_publisher = GroupAction(
        actions=[
            PushRosNamespace("oak"),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="oak_state_publisher",
                output="screen",
                parameters=[
                    {"robot_description": robot_description},
                    {"use_sim_time": use_sim_time},
                ],
            ),
        ]
    )

    # Pose args declared as REQUIRED (no default) — caller must pass them.
    pose_arg_decls = [DeclareLaunchArgument(name) for name in POSE_ARGS]

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use Gazebo simulation clock",
            ),
            *pose_arg_decls,
            camera_state_publisher,
        ]
    )
