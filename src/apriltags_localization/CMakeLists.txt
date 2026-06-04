cmake_minimum_required(VERSION 3.8)
project(apriltags_localization)

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



######################### Python related stuff #########################
ament_python_install_package(${PROJECT_NAME})

# install python programs
install(PROGRAMS
  apriltags_localization/detect_apriltags.py
  apriltags_localization/optimize_pose.py
  apriltags_localization/apriltag_world_localizer.py
  DESTINATION lib/${PROJECT_NAME}
)


############################ other stuff ############################
# install files and folders
install(
  DIRECTORY
    launch
    config
    rviz
  DESTINATION share/${PROJECT_NAME}
  )

ament_package()
