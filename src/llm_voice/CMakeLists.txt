cmake_minimum_required(VERSION 3.8)
project(llm_voice)

find_package(ament_cmake REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  ${PROJECT_NAME}/v5_pipecat_langgraph.py
  ${PROJECT_NAME}/v6_pipecat_langgraph.py

  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
