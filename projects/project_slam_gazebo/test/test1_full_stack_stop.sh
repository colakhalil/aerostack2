#!/usr/bin/env bash
# test1_full_stack_stop.sh
# test1_full_stack_launch.sh ile başlatılan tüm süreçleri temiz şekilde kapatır.

set +e

echo "[test1-stop] AS2 / Gazebo / RViz / SLAM süreçleri kapatılıyor..."

pkill -f "as2_keyboard_teleoperation"  2>/dev/null
pkill -f "slam_wrapper_py"             2>/dev/null
pkill -f "as2_behaviors_motion"        2>/dev/null
pkill -f "as2_motion_controller_node"  2>/dev/null
pkill -f "as2_state_estimator"         2>/dev/null
pkill -f "as2_platform_gazebo_node"    2>/dev/null
pkill -f "ros2 launch"                 2>/dev/null
pkill -f "rviz2"                       2>/dev/null
pkill -f "parameter_bridge"            2>/dev/null
pkill -f "ign gazebo"                  2>/dev/null
pkill -f "gz sim"                      2>/dev/null
pkill -f "ruby.*gz"                    2>/dev/null

sleep 1
echo "[test1-stop] Bitti."
