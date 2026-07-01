cmake_minimum_required(VERSION 3.8)
project(moveit_commander)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(std_msgs REQUIRED)
find_package(project_interfaces REQUIRED)

# c++ executables
add_executable(commander src/commander.cpp)
ament_target_dependencies(commander 
                                  rclcpp 
                                  moveit_ros_planning_interface 
                                  std_msgs 
                                  project_interfaces)
add_executable(test_commander src/test_commander.cpp)
ament_target_dependencies(test_commander
                                  rclcpp 
                                  std_msgs)

# install targets
install(TARGETS
  commander
  test_commander
  DESTINATION lib/${PROJECT_NAME}/
)

# Install directories
install(DIRECTORY
  config
  launch
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
