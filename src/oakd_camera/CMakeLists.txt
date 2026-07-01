cmake_minimum_required(VERSION 3.8)
project(oakd_camera)

# find dependencies
find_package(ament_cmake REQUIRED)

# install files and folders
install(
  DIRECTORY
    launch
    config
    rviz
    urdf
  DESTINATION share/${PROJECT_NAME}
  )

# Python node scripts (executable, invoked by name in launch).
install(PROGRAMS
  scripts/fix_camera_info.py
  DESTINATION lib/${PROJECT_NAME}
  )

ament_package()
