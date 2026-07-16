cmake_minimum_required(VERSION 3.8)
project(segment_grasppose)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})


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
  segment_grasppose/grasppose_server_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME grasppose_server
)

install(PROGRAMS
  segment_grasppose/test_grasppose_client_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME grasppose_client
)

install(PROGRAMS
  segment_grasppose/segment_then_grasp_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME segment_then_grasp
)



install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
