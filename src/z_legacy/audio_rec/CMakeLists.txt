cmake_minimum_required(VERSION 3.8)
project(audio_rec)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_srvs REQUIRED)
find_package(project_interfaces REQUIRED)
find_library(PORTAUDIO_LIB portaudio REQUIRED)


include_directories(
  include
  ${PORTAUDIO_INCLUDE_DIR}
)

# Install Python modules
ament_python_install_package(${PROJECT_NAME})


#c++ executables
# audio_capturer__node
add_executable(audio_capturer_node
  src/audio_common/audio_capturer_node.cpp
  src/audio_capturer_main.cpp
)
target_link_libraries(audio_capturer_node
  ${PORTAUDIO_LIB}
)
ament_target_dependencies(audio_capturer_node
  rclcpp
  std_srvs
  project_interfaces
)
install(TARGETS
  audio_capturer_node
  DESTINATION lib/${PROJECT_NAME}
)


# Install launch files
install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}/
)

# Install config files
install(DIRECTORY
  config
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
