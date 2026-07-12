# moveit_commander

C++ ROS2 node that wraps MoveIt2's `MoveGroupInterface`. Accepts joint commands, Cartesian pose commands, and gripper commands via ROS2 topics and executes them through MoveIt2 planning.

---

## Nodes: `commander_5dof` and `commander_6dof`

Both run in the `/follower` namespace and subscribe to the same topics. They are
identical except the `joint_command` guard: `commander_5dof` expects 5 arm values,
`commander_6dof` expects 6. Run whichever matches the loaded `move_group`
(`so101_moveit_5dof` or `so101_moveit_6dof`).

### Topics subscribed

| Topic | Type | Action |
|-------|------|--------|
| `joint_command` | `std_msgs/Float64MultiArray` | Move arm to joint positions (5 for `commander_5dof`, 6 for `commander_6dof`) |
| `pose_command` | `project_interfaces/PoseCommand` | Move arm to Cartesian pose (regular or Cartesian path) |
| `open_gripper` | `std_msgs/Bool` | `true` = open, `false` = close |

`joint_command` value order (chain order):

| Pos | 5dof | 6dof |
|-----|------|------|
| 0 | shoulder_pan | shoulder_pan |
| 1 | shoulder_lift | shoulder_lift |
| 2 | elbow_flex | elbow_flex |
| 3 | wrist_flex | wrist_flex |
| 4 | wrist_roll | wrist_yaw |
| 5 | — | wrist_roll |

### MoveIt2 planning groups used

| Group | Purpose |
|-------|---------|
| `arm` | 5-joint arm motion |
| `gripper` | Gripper open/close (named targets: `OPEN`, `CLOSE`, `OPEN_HALF`) |

---

## Files

| File | Purpose |
|------|---------|
| `src/commander_5dof.cpp` | Commander node (5dof arm) |
| `src/commander_6dof.cpp` | Commander node (6dof arm) |
| `src/test_commander_5dof.cpp` | Dev tool — publishes a fixed 5-joint command every 500ms |
| `src/test_commander_6dof.cpp` | Dev tool — publishes a fixed 6-joint command every 500ms |
| `launch/moveit_commander_5dof_launch.py` | Launches `commander_5dof` in `/follower` namespace |
| `launch/moveit_commander_6dof_launch.py` | Launches `commander_6dof` in `/follower` namespace |
| `config/moveit_commander_params.yaml` | Node parameters |

---

## Launch

```bash
# 5dof
ros2 launch moveit_commander moveit_commander_5dof_launch.py
# 6dof
ros2 launch moveit_commander moveit_commander_6dof_launch.py
```

MoveIt2 move_group must already be running. Use `so101_bringup` launch files to start the full stack.

---

## Dependencies

- `moveit_ros_planning_interface` — MoveIt2 C++ API
- `project_interfaces` — `PoseCommand` message
- `rclcpp`, `std_msgs`
