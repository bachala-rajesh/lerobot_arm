# moveit_commander

C++ ROS2 node that wraps MoveIt2's `MoveGroupInterface`. Accepts joint commands, Cartesian pose commands, and gripper commands via ROS2 topics and executes them through MoveIt2 planning.

---

## Node: `commander`

Runs in the `/follower` namespace.

### Topics subscribed

| Topic | Type | Action |
|-------|------|--------|
| `joint_command` | `std_msgs/Float64MultiArray` | Move arm to 5 joint positions |
| `pose_command` | `project_interfaces/PoseCommand` | Move arm to Cartesian pose (regular or Cartesian path) |
| `open_gripper` | `std_msgs/Bool` | `true` = open, `false` = close |

### MoveIt2 planning groups used

| Group | Purpose |
|-------|---------|
| `arm` | 5-joint arm motion |
| `gripper` | Gripper open/close (named targets: `OPEN`, `CLOSE`, `OPEN_HALF`) |

---

## Files

| File | Purpose |
|------|---------|
| `src/commander.cpp` | Main commander node |
| `src/test_commander.cpp` | Dev tool — publishes a fixed joint command every 500ms for testing |
| `launch/moveit_commander_launch.py` | Launches `commander` in `/follower` namespace |
| `config/moveit_commander_params.yaml` | Node parameters |

---

## Launch

```bash
ros2 launch moveit_commander moveit_commander_launch.py
```

MoveIt2 move_group must already be running. Use `so101_bringup` launch files to start the full stack.

---

## Dependencies

- `moveit_ros_planning_interface` — MoveIt2 C++ API
- `project_interfaces` — `PoseCommand` message
- `rclcpp`, `std_msgs`
