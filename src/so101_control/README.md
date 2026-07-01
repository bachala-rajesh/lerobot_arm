# so101_control

ros2_control YAML configs and controller launch files for the SO-101 arm (real robot + simulation).

---

## Config files

| File | Used for |
|------|---------|
| `so101_follower_controllers.yaml` | Follower arm — 5DOF (`dof:=5`) |
| `so101_follower_6dof_controllers.yaml` | Follower arm — 6DOF (`dof:=6`) |
| `so101_leader_controllers.yaml` | Leader arm — position read-only |
| `so101_leader_controllers_joint_states.yaml` | Leader arm — joint states only (no control) |

Each YAML defines which controllers the `controller_manager` loads:
- `joint_state_broadcaster` — publishes `/joint_states`
- `arm_controller` — `JointTrajectoryController` for joints 1–5
- `gripper_controller` — `JointTrajectoryController` for gripper

---

## Launch files

| File | What it does |
|------|-------------|
| `follower_joints_trajectory_control.launch.py` | Start trajectory controllers for follower arm |
| `follower_joints_position_control.launch.py` | Start position controllers for follower arm |
| `leader_joints_position_control.launch.py` | Start position controllers for leader arm |
| `leader_joints_states.launch.py` | Start joint state broadcaster only (leader, no commands) |

These launch files are not called directly — they are included by `so101_bringup` launch files.
