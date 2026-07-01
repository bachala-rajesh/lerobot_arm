# TODO — moveit_commander

- [ ] Add 6DOF arm support in `commander.cpp`. Currently the `Commander` class is hardcoded for 5 joints (`joints.size() == 5` check in `jointCmdCallback`). Need to handle the 6DOF variant where the arm group has 6 joints.
