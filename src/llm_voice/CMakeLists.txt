cmake_minimum_required(VERSION 3.8)
project(llm_voice)

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

# Install Python modules
ament_python_install_package(${PROJECT_NAME})

# Test client
install(PROGRAMS
  ${PROJECT_NAME}/v1_test_langchain.py
  ${PROJECT_NAME}/v2_test_langchain_scene_db.py
  ${PROJECT_NAME}/v3_test_langchain_pipecat_scene_db_tools.py
  ${PROJECT_NAME}/v4_test_langchain_pipecat.py
  ${PROJECT_NAME}/v5_pipecat_langgraph.py
  ${PROJECT_NAME}/v6_pipecat_langgraph.py

  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
