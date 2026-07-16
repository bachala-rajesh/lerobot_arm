# calibration_and_setup

One-off servo setup and calibration tools for the SO-101 arm, plus the live calibration data `so101_bringup`'s launch files consume.

---

## Scripts

| File | Purpose |
|------|---------|
| `scripts/set_servo_id.py` | Find a servo's current (unknown) ID by scan, then change it |
| `scripts/set_return_level.py` | Set Return_Level=2 on all servos of an arm |
| `scripts/5dof_set_home_offsets.py` | Compute + write home (zero) offsets — 5DOF arm (6 servos) |
| `scripts/6dof_set_home_offsets.py` | Compute + write home (zero) offsets — 6DOF arm (7 servos, wrist_yaw) |
| `scripts/5dof_find_joint_range.py` | Read-only: find range_min/range_max per joint — 5DOF arm |
| `scripts/6dof_find_joint_range.py` | Read-only: find range_min/range_max per joint — 6DOF arm |

Run directly with `python3`, or via `ros2 run calibration_and_setup <script_name>` after building.

---

## Config

| File | Purpose |
|------|---------|
| `config/5dof_so101_follower_calibration.yaml` | Follower servo calibration, 5DOF variant (6 servos) |
| `config/6dof_so101_follower_calibration.yaml` | Follower servo calibration, 6DOF variant (7 servos, wrist_yaw) |
| `config/so101_leader_calibration.yaml` | Leader servo calibration (leader is always 5DOF — no dof-prefixed variant) |
| `config/calibration_data_backup/` | Timestamped backups written by the scripts above |

**How this file is used:** `so101_bringup`'s real-robot launch files (`real_follower_traj.launch.py`, `real_follower_pos.launch.py`, `real_leader.launch.py`, `real_leader_pos.launch.py`) read these yaml paths via `get_package_share_directory('calibration_and_setup')` and pass them into the URDF as `joint_config_file`. `feetech_ros2_driver` then **writes these values into the servo's EEPROM on every launch** — the yaml is the source of truth, not whatever is currently stored on the servo. Edit the yaml, don't rely on the servo remembering a one-off write.

Follower launch files pick `5dof_...` or `6dof_...` automatically based on the `dof` launch argument (`dof:=5` or `dof:=6`). Leader launch files always use the single `so101_leader_calibration.yaml`, since the leader arm is always 5DOF.
