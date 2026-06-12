cmake_minimum_required(VERSION 3.8)
project(scene_db)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

# Install the Python package (so other packages can import scene_db.database)
ament_python_install_package(${PROJECT_NAME})

# CLI: inspect_db
install(PROGRAMS
  ${PROJECT_NAME}/inspect_db.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME inspect_db
)

# Config dir (db path defaults, etc.)
install(DIRECTORY
  config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
