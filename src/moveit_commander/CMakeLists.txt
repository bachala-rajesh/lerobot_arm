cmake_minimum_required(VERSION 3.8)
project(moveit_commander)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(std_msgs REQUIRED)
find_package(project_interfaces REQUIRED)

# c++ executables
add_executable(commander_5dof src/commander_5dof.cpp)
ament_target_dependencies(commander_5dof
                                  rclcpp
                                  moveit_ros_planning_interface
                                  std_msgs
                                  project_interfaces)
add_executable(commander_6dof src/commander_6dof.cpp)
ament_target_dependencies(commander_6dof
                                  rclcpp
                                  moveit_ros_planning_interface
                                  std_msgs
                                  project_interfaces)
add_executable(test_commander_5dof src/test_commander_5dof.cpp)
ament_target_dependencies(test_commander_5dof
                                  rclcpp
                                  std_msgs)
add_executable(test_commander_6dof src/test_commander_6dof.cpp)
ament_target_dependencies(test_commander_6dof
                                  rclcpp
                                  std_msgs)

# install targets
install(TARGETS
  commander_5dof
  commander_6dof
  test_commander_5dof
  test_commander_6dof
  DESTINATION lib/${PROJECT_NAME}/
)

# Install directories
install(DIRECTORY
  config
  launch
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
