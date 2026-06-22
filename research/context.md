# Robot + Software Context

Single source of truth for hardware and software facts.
All agents read from HERE — do not read hardware sections from CLAUDE.md.

Last updated: 2026-06-18

---

## Robot

| Item | Detail |
|------|--------|
| Robot | SO-101 LeRobot robotic arm |
| Build | 3D printed — physical shape CAN be modified (skin, covers, attachments) |
| Servos | Feetech STS3215 |
| Total joints | 6 (5 arm + 1 gripper) |
| Arms | TWO: leader (human teleoperates) + follower (robot actuated) |
| Leader arm | Optional input — NOT mandatory for ideas |

### Joint order (fixed — do not change)

| # | Joint name |
|---|-----------|
| 1 | shoulder_pan |
| 2 | shoulder_lift |
| 3 | elbow_flex |
| 4 | wrist_flex |
| 5 | wrist_roll |
| 6 | gripper (separate controller) |

"Arm" = joints 1–5. Gripper always handled separately.

---

## Sensors and Cameras

| Device | Location | Status |
|--------|----------|--------|
| OAK-D depth camera | Fixed on stand, facing the robot | Active |
| Wrist camera | Attached to robot arm, moves with it | Active |
| ReSpeaker 6-channel mic (xvf3800) | Not connected yet | Coming soon |

---

## Compute

| Machine | Role | Note |
|---------|------|------|
| Laptop — Ubuntu 22.04 | Development and testing | **Primary target — test here first** |
| Jetson Orin NX | Deployment target | Only after laptop works. Compute is LIMITED — check RAM and GPU usage |

**Development order:** Always test on laptop first. Jetson deployment comes later.
Do NOT optimize for Jetson at the initial implementation stage.

---

## Software Stack

| Item | Detail |
|------|--------|
| OS | Ubuntu 22.04 |
| ROS2 | Humble |
| Languages | Python (primary) + C++ |
| MoveIt2 | Planning group: `arm` (5 joints). Gripper group separate. |

### ROS2 Topics

| Topic | Purpose |
|-------|---------|
| `/leader/joint_states` | Leader arm state |
| `/follower/joint_states` | Follower arm state |
| `/follower/arm_controller/joint_trajectory` | Send trajectory to arm (5 joints) |
| `/follower/gripper_controller/joint_trajectory` | Send trajectory to gripper |

---

## AI and LLM Constraints (read this carefully)

| Rule | Detail |
|------|--------|
| **Allowed** | Qwen models via aliyuncs.com (dashscope API) |
| **NOT allowed** | OpenAI, Google AI, any cloud API at runtime |
| Text / code / reasoning | `qwen-max` or `qwen-plus` |
| Vision / depth | `qwen-vl` |
| Lightweight / fast | `qwen-turbo` (for Jetson-side tasks) |
| **Runtime policy** | Offline-first — all inference must work without internet |

Any paper or approach that requires OpenAI or Google APIs at runtime = **skip**.

---

## What This Setup CAN Do

- 5-DOF expressive arm motion + gripper open/close
- Scene understanding: OAK-D (fixed viewpoint, depth available)
- Robot POV vision: wrist camera (moves with arm, sees what arm sees)
- 3D object positions from OAK-D depth data
- Human gesture recording via leader arm teleop
- Voice commands: coming soon (ReSpeaker — ideas using voice are valid)
- Physical modification: 3D printed body → can add skin, shapes, covers

---

## What This Setup CANNOT Do

- Mobile base — arm is stationary
- Force/torque sensing
- Tactile skin
- Cloud AI at runtime (OpenAI/Google blocked)
- More than 5 arm DOF
- Multiple follower arms
