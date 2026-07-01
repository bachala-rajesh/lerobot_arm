cmake_minimum_required(VERSION 3.8)
project(segment_grasppose)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  segment_grasppose/segment_grasppose_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME segment_grasppose_node
)

install(PROGRAMS
  test_client.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
