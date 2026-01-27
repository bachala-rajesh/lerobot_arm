cmake_minimum_required(VERSION 3.8)
project(moveit_commander)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(std_msgs REQUIRED)
find_package(so101_interfaces REQUIRED)
find_package(ament_cmake_gtest REQUIRED)


if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

# Install Python modules
ament_python_install_package(${PROJECT_NAME})


# c++ executables
add_executable(commander src/commander.cpp)
ament_target_dependencies(commander 
                                  rclcpp 
                                  moveit_ros_planning_interface 
                                  std_msgs 
                                  so101_interfaces)
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
