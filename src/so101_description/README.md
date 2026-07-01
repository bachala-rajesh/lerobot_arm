# so101_description

URDF and mesh files for the SO-101 robot arm. Two variants: **5DOF** and **6DOF**.

---

## How the URDF files connect

```
so101_arm_with_control.urdf.xacro          ← ENTRY POINT (used by all launch files)
│
├── args: dof_type (dof_5 | dof_6)
│         sim_mode (real_robot | gazebo | isaacsim)
│         arm_prefix (follower | leader)
│
├── [dof_type == dof_5] → urdf/robots/5dof_so101_arm.urdf.xacro
│                              └── meshes from: 5dof_meshes/
│
├── [dof_type == dof_6] → urdf/robots/6dof_so101_arm.urdf.xacro
│                              └── meshes from: 6dof_meshes/
│
└── [sim_mode, unless moveit_status=true]
      ├── real_robot  → urdf/ros2_control/real_so101_follower_ros2_control.urdf
      ├── gazebo      → urdf/ros2_control/sim_gazebo_so101_follower_ros2_control.urdf
      └── isaacsim   → urdf/ros2_control/sim_isaacsim_so101_follower_ros2_control.urdf
```

### Other URDF files (standalone, not included by the entry point in the above urdf files)

| File | Purpose |
|------|---------|
| `urdf/scene.urdf` | World frame + table only — loaded separately in Gazebo launch |
| `urdf/apriltag_markers/apriltag.urdf.xacro` | AprilTag marker robot — spawned separately for localization |
| `urdf/apriltag_markers/apriltag_marker.xacro` | Single marker macro, included by `apriltag.urdf.xacro` |

---

## 5DOF vs 6DOF

| | 5DOF | 6DOF |
|-|------|------|
| Joints | shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll | + wrist_yaw between wrist_flex and wrist_roll |
| Servo IDs | 1–5 (arm), 6 (gripper) | 1–6 (arm), 7 (gripper) |
| Meshes | `5dof_meshes/` | `6dof_meshes/` |

---

## Launch files

| File | What it loads |
|------|--------------|
| `follower_description.launch.py` | Follower arm URDF + robot_state_publisher |
| `leader_description.launch.py` | Leader arm URDF + robot_state_publisher |
| `leader_follower_description.launch.py` | Both arms together |
| `debug_display.launch.py` | Single arm + RViz for URDF inspection |

### Choosing 5DOF or 6DOF

Pass `dof` argument to any launch file (default: `5`):

```bash
# 5DOF (default)
ros2 launch so101_description follower_description.launch.py dof:=5

# 6DOF
ros2 launch so101_description follower_description.launch.py dof:=6
```
