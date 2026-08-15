# lerobot_ws

ROS2 Humble workspace for the **SO-101** robot arm (LeRobot project, Feetech
STS3215 servos).

## About

The project has **two arms**: a **leader** (moved by hand to teleoperate) and
a **follower** (the one that actually acts). The follower comes in two
hardware variants — **5DOF** and **6DOF** (the 6DOF adds a `wrist_yaw`
joint) — each with its own URDF, MoveIt2 config, and Gazebo setup. Everything
runs on **ROS2 Humble**, with **Gazebo simulation** fully set up alongside
real-hardware control, so the same launch pattern works in sim or on the
physical arm.

On top of the arm stack, the project adds two AI layers:

- **Voice agent** — built with **Pipecat** for the real-time audio pipeline
  (STT → LLM → TTS), orchestrated by **LangGraph** for tool use and
  multi-step reasoning. **Qwen models** (via Alibaba DashScope) power all
  three roles: speech-to-text, the LLM reasoning/tool-calling, and
  text-to-speech. The agent can call ROS2 tools — e.g. asking it to look at
  the table and describe what it sees.
- **Vision-driven grasping** — a **VLM** (vision-language model) finds and
  localizes the target object in the scene from a natural-language
  description; that detection feeds a grasp-pose pipeline (SAM2 + AnyGrasp)
  that turns it into a graspable pose for the follower arm.

Both AI layers are **in progress** — see [Status at a glance](#status-at-a-glance)
below.

Every package below has its own `README.md` with full detail. This file is
the map — read the package README before the code.

---

## Status at a glance

| Area | Status |
|---|---|
| Arm control (real + Gazebo + Isaac Sim), MoveIt2, teleop, calibration | ✅ Working |
| Camera (OAK-D), AprilTag localization, VLM object detection, scene memory | ✅ Working |
| **Grasping (SAM2 + AnyGrasp)** | 🚧 **Not finished** — stub pipeline, models not wired in |
| **Voice agent (Pipecat + LangGraph)** | 🚧 **Not finished** — working prototype script, no launch file, no ROS node yet |

---

## Repository layout

```
lerobot_ws/
├── src/
│   ├── so101_description/       # URDF + meshes (5DOF / 6DOF)
│   ├── so101_control/           # ros2_control YAML + controller launch
│   ├── so101_bringup/           # top-level launch files (real / gz / isaacsim / moveit)
│   ├── so101_moveit_5dof/       # MoveIt2 config, 5DOF
│   ├── so101_moveit_6dof/       # MoveIt2 config, 6DOF
│   ├── moveit_commander/        # C++ node wrapping MoveGroupInterface
│   ├── calibration_and_setup/   # servo ID / home offset / joint range scripts
│   ├── joy_teleop/              # gamepad → TwistStamped for MoveIt Servo
│   │
│   ├── oakd_camera/             # OAK-D camera launch/config (real + sim)
│   ├── point_clouds/            # point cloud processing
│   ├── localization/
│   │   ├── apriltags_localization/  # AprilTag world localizer
│   │   └── scene_localizer/         # fills 3D coords into scene_db
│   ├── vlm_perception/          # Qwen-VL object detection service
│   ├── scene_db/                # SQLite scene memory (Python library, no node)
│   │
│   ├── segment_grasppose/       # 🚧 SAM2 + AnyGrasp grasp pose estimation — STUB
│   ├── deep_learning_models/    # empty — model weights go here
│   ├── system_setup/            # AnyGrasp/GraspNet install notes (not a ROS package)
│   │
│   ├── llm_voice/               # 🚧 Pipecat + LangGraph voice agent — WIP
│   │
│   ├── project_interfaces/      # custom msg/srv/action, shared by all of the above
│   ├── 3rd_party_libraries/     # vendored: feetech_ros2_driver, ros2_numpy
│   │
│   ├── problems_faced.md        # known bugs + root causes — CHECK BEFORE DEBUGGING
│   ├── commands.md              # ad-hoc ros2 commands log
│   └── TODO                     # active task list per area
│
├── research/                    # grasp-model literature notes (not user-facing docs)
├── CHANGELOG.md                 # milestone log
└── .mcp.json / .asoundrc        # MCP + audio device config (used by llm_voice)
```

`z_legacy/`, `z_notes/`, `z_plans/`, `z_results/`, `z_temp/`, `z_links_references/`
are scratch — ignore unless you're told otherwise.

---

## Build & run

```bash
colcon build --symlink-install                      # whole workspace
colcon build --symlink-install --packages-select <pkg>   # one package
source install/setup.bash                            # every new shell, after every build
ros2 launch <pkg> <launch_file>.launch.py
```

`so101_bringup` launch files follow `{env}_{who}_{ctrl}.launch.py`
(`env`=real|gz|isaacsim|moveit, `who`=follower|leader|teleop,
`ctrl`=pos|traj). See `src/so101_bringup/README.md` for the full table.

---

## Hardware

| Item | Detail |
|---|---|
| Arm | SO-101, Feetech STS3215 servos |
| Variants | 5DOF (6 servos) and 6DOF (7 servos, adds `wrist_yaw`) |
| Arms | `leader` (manual input), `follower` (actuated) |
| Camera | Luxonis OAK-D |
| Joint order | shoulder_pan → shoulder_lift → elbow_flex → wrist_flex → (wrist_yaw, 6DOF only) → wrist_roll → gripper (separate controller) |

---

## 🚧 Grasping — not finished

`segment_grasppose` (SAM2 + AnyGrasp) is a **stub**: the service
(`/segment_grasppose/find_grasp_pose`) and message flow exist, but the SAM2
segmentation call and the AnyGrasp inference call are still TODO in the node.
The AnyGrasp SDK itself is installed and tested standalone (conda env, see
`src/system_setup/setup_anygrasp.md`) — the remaining work is wiring it into
the ROS node. `deep_learning_models/models/` is empty, waiting for weights.

## 🚧 Voice agent — not finished

`llm_voice` (Pipecat + LangGraph + Qwen via DashScope) has a working
prototype script (`v5_pipecat_langgraph.py`) with STT, TTS, and ROS2 tool
calls (`detect_objects`, `scene_db` query, etc.), run directly with
`python3` — there is no launch file or ROS node wrapper yet. Requires
`DASHSCOPE_API_KEY` and MoveIt2 + `vlm_perception` running for the ROS tools
to work. See `src/llm_voice/README.md`.

---

## Known issues

Check `src/problems_faced.md` before debugging anything — it already has
root causes for the trickiest bugs (trajectory timing, MoveIt namespacing,
6DOF Gazebo crashes, octomap misalignment, AnyGrasp install snags). One is
still open: 6DOF right-jaw mimic joint breaks MoveIt in Gazebo (`right_jaw_slider_mimic`
not found) — current workaround makes the gripper asymmetric in sim only.

---

## Where to look next

| Question | File |
|---|---|
| What's actively being worked on | `src/TODO` |
| What changed recently (milestones) | `CHANGELOG.md` |
| Ad-hoc ros2 commands that work | `src/commands.md` |
| Package-specific detail | `<package>/README.md` |
