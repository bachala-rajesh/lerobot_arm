# Workspace Changes Log

---

## 2026-07-01 — Workspace Maintenance Session

**Date:** 2026-07-01
**Time:** 12:20 CST
**Branch:** `dev`

All changes committed to git. Each package was cleaned up with the same goals:
- Proper `README.md` per package
- Fixed `package.xml` (version, maintainer, license, description)
- Cleaned `CMakeLists.txt` (removed C++ compiler flags block, `BUILD_TESTING` lint block, unused deps)
- Removed `test_depend` entries (no real tests exist)
- Moved unused/legacy files to `legacy/` folder where applicable

---

### project_interfaces (renamed from `so101_interfaces`)

- Package renamed: `so101_interfaces` → `project_interfaces`
- Python package dir renamed: `so101_interfaces/` → `project_interfaces/`
- Fixed internal cross-references in `.msg` and `.action` files:
  - `Audio.msg`: `so101_interfaces/AudioData` → `project_interfaces/AudioData`
  - `AudioStamped.msg`: `so101_interfaces/Audio` → `project_interfaces/Audio`
  - `TTS.action`: `so101_interfaces/AudioStamped` → `project_interfaces/AudioStamped`
- Updated all dependent packages: `vlm_perception`, `moveit_commander`, `segment_grasppose`, `llm_voice` (v1, v4, v5, v6)
- `package.xml`: version 0.1.0, Apache-2.0, maintainer fixed
- `CMakeLists.txt`: removed C++ compiler flags + `BUILD_TESTING` block
- `README.md`: created — file name + purpose only

---

### so101_description

- `package.xml`: fixed maintainer (was `forgetwhatuwant@gmail.com` / `hls`), Apache-2.0, version 0.1.0
- `CMakeLists.txt`: removed C++ compiler flags + `BUILD_TESTING` block
- URDF argument renamed: `dof_type` → `dof`, values `dof_5`/`dof_6` → `5`/`6` (applied across 20 files in description, control, bringup packages)
- `urdf/robots/6dof_so101_arm.urdf.xacro` moved to `legacy/` via `git mv`
- `README.md`: created with ASCII URDF tree diagram, DOF selection table

---

### so101_control

- `package.xml`: maintainer, Apache-2.0, version 0.1.0
- Deleted boilerplate linter test stubs: `test/test_copyright.py`, `test/test_flake8.py`, `test/test_pep257.py`
- Removed `test_depend` entries
- `README.md`: created with config files table and launch files table

---

### joy_teleop (renamed from `so101_teleop`)

- Package renamed: `so101_teleop` → `joy_teleop` (generic name, usable on other robots)
- Folder, Python package dir, resource marker, launch file, node file all renamed
- `package.xml`: fixed wrong description ("biped"), maintainer, license, version
- Deleted 3 boilerplate linter test stubs
- `README.md`: created

---

### so101_moveit_5dof (renamed from `s0101_moveit_5dof` — typo fix)

- Typo fixed: `s0101_moveit_5dof` → `so101_moveit_5dof` (letter `s0` was `s` + `zero`, not `so`)
- All internal launch files updated; `so101_bringup` references updated
- `package.xml`: removed duplicate `exec_depend` entries, fixed description
- `README.md`: created

---

### so101_moveit_6dof (renamed from `so101_6dof_moveit_config`)

- Package renamed: `so101_6dof_moveit_config` → `so101_moveit_6dof` (consistent with 5dof)
- All internal launch files + `so101_bringup` references updated
- `package.xml`: removed duplicate `exec_depend` entries
- `README.md`: created

---

### oakd_camera

- `package.xml`: fixed maintainer (was `todo@todo.todo` / `rajesh`), version 0.1.0
- `CMakeLists.txt`: removed C++ flags, `BUILD_TESTING` block, commented-out `find_package` line
- Launch files renamed (3 active files):
  - `oakd_camera_launch.py` → `real.launch.py`
  - `oakd_camera_rsp.launch.py` → `sim_rsp.launch.py`
  - `oakd_sim_pointcloud.launch.py` → `sim_pointcloud.launch.py`
- 4 launch files moved to `legacy/`:
  - `oakd_camera_with_pointclouds.launch.py`
  - `oakd_pointclouds_stereo.launch.py`
  - `test_oakd_camera_launch.py`
  - `test_oakd_isaac_launch.py`
- Updated `so101_bringup/gz_follower.launch.py` references
- `README.md`: rewritten

---

### vlm_perception (renamed from `vlm`)

- Package renamed: `vlm` → `vlm_perception`
- Python package dir renamed: `vlm/` → `vlm_perception/`
- `package.xml`: version 0.1.0, Apache-2.0, fixed description
- `CMakeLists.txt`: removed C++ flags + `BUILD_TESTING` block
- `launch/vlm.launch.py`: updated package name references
- `README.md`: created — includes API key setup instructions

---

### scene_db

- `package.xml`: version 0.1.0, Apache-2.0, removed `test_depend` entries
- `CMakeLists.txt`: removed C++ flags + `BUILD_TESTING` block
- `scene.db`: untracked from git (runtime data should not be in version control)
- `*.db` added to workspace `.gitignore`
- `scene_db/test_db.py` moved to `legacy/`
- `README.md`: created — Python API, CLI usage, schema table

---

### localization/apriltags_localization

- `package.xml`: maintainer fixed (was `todo@todo.todo` / `rajesh`), version 0.1.0, removed `test_depend`
- `CMakeLists.txt`: removed C++ flags, `BUILD_TESTING` block, removed nonexistent `rviz` dir from install
- `README.md`: rewritten — removed emojis, fixed broken code blocks, added tables

---

### localization/scene_localizer

- `package.xml`: version 0.1.0, Apache-2.0, removed `test_depend`
- `CMakeLists.txt`: removed C++ flags, `BUILD_TESTING` block, removed `localizer_practice.py` from install
- `README.md`: created — flow diagram, config params table

---

### moveit_commander

- `package.xml`: version 0.1.0, Apache-2.0, description added, removed `test_depend` + `ament_cmake_gtest`
- `CMakeLists.txt`: removed C++ flags, `BUILD_TESTING` block, unused `ament_cmake_gtest`, empty Python install
- `moveit_commander/__init__.py`: deleted (empty, unused)
- `README.md`: created — topics, MoveIt2 groups, launch info
- `TODO.md`: created — note to add 6DOF support in `commander.cpp`

---

### segment_grasppose

- `package.xml`: version 0.1.0, maintainer email corrected (was `ravi6703@gmail.com`)
- `README.md`: created — pipeline diagram, stub status note

---

### llm_voice

- `package.xml`: version 0.1.0, Apache-2.0, fixed description typos (`assitant` → `assistant`, `langraph` → `LangGraph`), removed `test_depend`
- `CMakeLists.txt`: removed C++ flags + `BUILD_TESTING` block
- `README.md`: created — pipeline overview, all services/processors/frames/tools documented

---

### so101_bringup

- `package.xml`: version 0.1.0, Apache-2.0, maintainer fixed (was `todo@todo.todo` / `mira`)
- `CMakeLists.txt`: removed C++ flags + `BUILD_TESTING` block
- **17 launch files renamed** using consistent pattern `{env}_{who}_{ctrl}.launch.py`:

| Old name | New name |
|----------|----------|
| `real_follower_with_position_control.launch.py` | `real_follower_pos.launch.py` |
| `real_follower_with_trajectory_control.launch.py` | `real_follower_traj.launch.py` |
| `real_leader_with_position_control.launch.py` | `real_leader_pos.launch.py` |
| `real_leader_follower_with_control.launch.py` | `real_teleop_traj.launch.py` |
| `real_leader_follower_with_leader_position_control.launch.py` | `real_teleop_ldr_pos.launch.py` |
| `real2sim_with_control.launch.py` | `real_to_sim.launch.py` |
| `follower_gazebo.launch.py` | `gz_follower.launch.py` |
| `follower_gazebo_with_position_control.launch.py` | `gz_follower_pos.launch.py` |
| `follower_gazebo_with_trajectory_control.launch.py` | `gz_follower_traj.launch.py` |
| `leader_follower_gazebo.launch.py` | `gz_teleop.launch.py` |
| `leader_follower_gazebo_control.launch.py` | `gz_teleop_traj.launch.py` |
| `isaacsim_with_position_control.launch.py` | `isaacsim_follower_pos.launch.py` |
| `isaacsim_with_trajectory_control.launch.py` | `isaacsim_follower_traj.launch.py` |
| `moveit_server_real.launch.py` | `moveit_real.launch.py` |
| `moveit_server_sim.launch.py` | `moveit_gz_5dof.launch.py` |
| `moveit_server_sim_6dof.launch.py` | `moveit_gz_6dof.launch.py` |

- `debug_moveit_config.py` moved to `legacy/` (empty file, missing `.launch.py` suffix)
- All internal cross-references updated across affected launch files
- `README.md`: created — full launch file reference table

---

### Workspace-level

- `.gitignore`: added `*.db` rule (prevents SQLite database files from being committed)
