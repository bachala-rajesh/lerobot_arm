cmake_minimum_required(VERSION 3.8)
project(so101_description)

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)


install(
    DIRECTORY 
    urdf 
    launch 
    rviz 
    5dof_meshes
    6dof_meshes
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
