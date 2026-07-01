cmake_minimum_required(VERSION 3.8)
project(so101_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

if(POLICY CMP0148)
  cmake_policy(SET CMP0148 OLD)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)


rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/PoseCommand.msg"
  "msg/AudioData.msg"
  "msg/AudioInfo.msg"
  "msg/Audio.msg"
  "msg/AudioStamped.msg"
  "action/TTS.action"
  "action/SegmentObject.action"
  "srv/MusicPlay.srv"
  "srv/DetectObjects.srv"
  "srv/FindGraspPose.srv"
  DEPENDENCIES std_msgs geometry_msgs
)

ament_export_dependencies(
  std_msgs
  geometry_msgs
  rosidl_default_runtime
)

ament_package()
