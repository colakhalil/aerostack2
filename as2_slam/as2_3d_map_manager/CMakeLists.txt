cmake_minimum_required(VERSION 3.5)
project(as2_3d_map_manager)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Python module + entry point
ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  scripts/map_manager_py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  config/
  DESTINATION share/${PROJECT_NAME}/config
)

install(DIRECTORY
  launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

ament_package()
