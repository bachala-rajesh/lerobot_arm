cmake_minimum_required(VERSION 3.8)
project(vlm_perception)

find_package(ament_cmake REQUIRED)

# Install Python package
ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  ${PROJECT_NAME}/vlm_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME vlm_node
)

install(PROGRAMS
  ${PROJECT_NAME}/test_client.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  config
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
