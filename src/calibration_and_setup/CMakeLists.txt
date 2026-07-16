cmake_minimum_required(VERSION 3.8)
project(calibration_and_setup)

find_package(ament_cmake REQUIRED)

install(PROGRAMS
    scripts/set_servo_id.py
    scripts/5dof_set_home_offsets.py
    scripts/6dof_set_home_offsets.py
    scripts/5dof_find_joint_range.py
    scripts/6dof_find_joint_range.py
    scripts/set_return_level.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  config
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
