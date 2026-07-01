# so101_teleop

Joystick teleop node for the SO-101 arm. Reads gamepad input and publishes `TwistStamped` delta commands for MoveIt Servo.

---

## Node: `so101_teleop_node`

| | |
|-|-|
| Subscribes | `/joy` (`sensor_msgs/Joy`) |
| Publishes | `delta_twist_cmds` (`geometry_msgs/TwistStamped`) |
| Executor | MultiThreadedExecutor — joy callback and timer run in parallel |
| Timer rate | 10 Hz |

---

## Config: `so101_teleop_params.yaml`

Two-layer structure:

**Layer 1 — `joy_layout`:** Maps logical names to hardware indices.
```yaml
joy_layout:
  axes:
    left_stick_x: 0
    left_stick_y: 1
    ...
  buttons:
    triangle: 3
    ...
```

**Layer 2 — `teleop_control_map`:** Binds robot actions to logical names from Layer 1.
```yaml
teleop_control_map:
  locomotion_control:
    linear_x: "left_stick_x"
    pitch: "right_stick_y"
    ...
  scale_control:
    speed_scale: "triangle"
```

To remap controls: change Layer 2 only. To support a new gamepad: change Layer 1 only.

---

## Launch

```bash
ros2 launch so101_teleop so101_teleop_launch.py
```

Not usually called directly — included by `so101_bringup` launch files that start MoveIt Servo.
