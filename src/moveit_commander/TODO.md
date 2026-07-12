# TODO — moveit_commander

- [x] Add 6DOF arm support. Done via a separate `commander_6dof` node
      (`src/commander_6dof.cpp`) instead of editing `commander.cpp`, so 6dof-only
      features can grow without touching the 5dof node. The `joint_command`
      guard there expects 6 values; the extra joint is `wrist_yaw`.
