cmake_minimum_required(VERSION 3.8)
project(test_pkg)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find_package(Open3D REQUIRED
#   HINTS $ENV{HOME}/open3d_install/lib/cmake/Open3D
# )

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


# Install Python executables
install(PROGRAMS
  test_pkg/ros2_quintic_waypoints.py
  test_pkg/ros2_perlin_noise.py
  test_pkg/ros2_perlin_noise_rolling.py
  DESTINATION lib/${PROJECT_NAME}
)


# add_executable(test_open3d src/test_open3d.cpp)
# target_link_libraries(test_open3d Open3D::Open3D)

# install(TARGETS test_open3d DESTINATION lib/${PROJECT_NAME})


ament_package()
