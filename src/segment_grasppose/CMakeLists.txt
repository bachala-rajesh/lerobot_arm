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
  segment_grasppose/sam2_service_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME sam2_service_node
)

install(PROGRAMS
  segment_grasppose/test_sam2_service_client.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME test_service_client
)

install(PROGRAMS
  segment_grasppose/grasppose_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME grasppose_node
)



install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
