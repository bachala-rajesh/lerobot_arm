# so101_bringup

Top-level bringup package for the SO-101 arm. All launch files follow this naming pattern:

```
{env}_{who}_{ctrl}.launch.py
env  : real | gz | isaacsim | moveit
who  : follower | leader | teleop (leader+follower)
ctrl : pos (position) | traj (trajectory)  — omitted for base launches
```

---

## Real robot

| Launch file | What starts |
|-------------|-------------|
| `real_follower_pos.launch.py` | Follower arm + position control |
| `real_follower_traj.launch.py` | Follower arm + trajectory control |
| `real_leader.launch.py` | Leader arm only (RSP + TF, no control) |
| `real_leader_pos.launch.py` | Leader arm + position control |
| `real_teleop_traj.launch.py` | Leader + follower + trajectory control (teleop) |
| `real_teleop_ldr_pos.launch.py` | Leader (position) + follower (trajectory) |
| `real_to_sim.launch.py` | Real leader → Gazebo follower mirror |

---

## Gazebo simulation

| Launch file | What starts |
|-------------|-------------|
| `gz_follower.launch.py` | Gazebo world + follower robot (base, no control) |
| `gz_follower_pos.launch.py` | Gazebo follower + position control |
| `gz_follower_traj.launch.py` | Gazebo follower + trajectory control |
| `gz_teleop.launch.py` | Gazebo world + leader + follower (base, no control) |
| `gz_teleop_traj.launch.py` | Gazebo leader + follower + trajectory control |

---

## Isaac Sim

| Launch file | What starts |
|-------------|-------------|
| `isaacsim_follower_pos.launch.py` | Isaac Sim follower + position control |
| `isaacsim_follower_traj.launch.py` | Isaac Sim follower + trajectory control |

---

## MoveIt2

| Launch file | What starts |
|-------------|-------------|
| `moveit_real.launch.py` | MoveIt2 move_group for real robot (5DOF) |
| `moveit_gz_5dof.launch.py` | MoveIt2 move_group for Gazebo sim (5DOF) |
| `moveit_gz_6dof.launch.py` | MoveIt2 move_group for Gazebo sim (6DOF) |

---

## Python scripts

| File | Purpose |
|------|---------|
| `so101_bringup/gui_sliders_arm_control.py` | GUI sliders to manually command joint positions |
| `so101_bringup/leader_follower_relay.py` | Relay node: copies leader joint states → follower trajectory commands |

---

## Config

| File | Purpose |
|------|---------|
| `config/gz_bridge.yaml` | Gazebo ↔ ROS2 topic bridge config |

Servo calibration yaml files (`so101_follower_calibration.yaml`, `so101_leader_calibration.yaml`) and their timestamped backups now live in the `calibration_and_setup` package — launch files here read them via `get_package_share_directory('calibration_and_setup')`.

---

## Other

| Path | Purpose |
|------|---------|
| `rviz/moveit.rviz` | RViz config for MoveIt2 |
| `rviz/vis.rviz` | RViz config for general visualization |
| `world/ignition_worlds/robot_arm_world.sdf` | Gazebo world SDF |
| `lerobot/` | LeRobot utility imports (error types, encoding utils) |

Servo setup/calibration scripts (set motor ID, set home offsets, set return level) moved to `calibration_and_setup` package.
