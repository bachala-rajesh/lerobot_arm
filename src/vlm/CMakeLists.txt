cmake_minimum_required(VERSION 3.8)
project(vlm)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

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



find_package(rclpy REQUIRED)

# Add Python node vlm_node
install(PROGRAMS
  ${PROJECT_NAME}/vlm_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME vlm_node
)

# Test client
install(PROGRAMS
  ${PROJECT_NAME}/test_client.py
  ${PROJECT_NAME}/v1_test_langchain.py
  ${PROJECT_NAME}/v2_test_langchain_scene_db.py
  ${PROJECT_NAME}/v3_test_langchain_pipecat_scene_db_tools.py
  ${PROJECT_NAME}/v4_test_langchain_pipecat.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install config + launch directories so launch files can find them
# via get_package_share_directory("vlm").
install(DIRECTORY
  config
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
