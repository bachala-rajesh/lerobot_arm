cmake_minimum_required(VERSION 3.8)
project(scene_db)

find_package(ament_cmake REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  ${PROJECT_NAME}/inspect_db.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME inspect_db
)

install(DIRECTORY
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
