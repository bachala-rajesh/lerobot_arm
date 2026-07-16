cmake_minimum_required(VERSION 3.8)
project(so101_bringup)

find_package(ament_cmake REQUIRED)

ament_python_install_package(${PROJECT_NAME})

# lerobot python package install
ament_python_install_package(lerobot)




# Install Python executables (ROS nodes)
install(PROGRAMS
    so101_bringup/gui_sliders_arm_control.py
    so101_bringup/leader_follower_relay.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install files
install(DIRECTORY
  launch
  rviz
  config
  world
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
