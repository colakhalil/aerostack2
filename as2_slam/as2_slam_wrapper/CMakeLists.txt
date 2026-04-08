cmake_minimum_required(VERSION 3.5)
project(as2_slam_wrapper)

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(as2_core REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)

set(PROJECT_DEPENDENCIES rclcpp as2_core sensor_msgs nav_msgs geometry_msgs tf2 tf2_ros)

# C++ executable (skeleton — kept for future C++ backend)
add_executable(slam_wrapper_node src/slam_wrapper_node.cpp)
ament_target_dependencies(slam_wrapper_node ${PROJECT_DEPENDENCIES})

install(TARGETS
  slam_wrapper_node
  DESTINATION lib/${PROJECT_NAME}
)

# Python module + entry point
ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  scripts/slam_wrapper_py
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

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
