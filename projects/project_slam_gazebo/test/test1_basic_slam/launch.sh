#!/usr/bin/env bash
# test1_basic_slam/launch.sh — Temel SLAM testi (slam_single dünya, engelsiz)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_NAME="test1"
source "$SCRIPT_DIR/../_common.sh"

CONFIG_FILE="$PROJECT_DIR/config/slam_single.json"
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config bulunamadı: $CONFIG_FILE"; exit 1
fi

# Eski logları temizle
rm -f "$LOG_DIR"/${TEST_NAME}_t*.log

echo "[$TEST_NAME] Temel SLAM stack başlatılıyor (slam_single)"
echo "[$TEST_NAME] Loglar: $LOG_DIR/"

open_window 1 "Sim" \
  "$SOURCE_CMD && ros2 launch $PROJECT_DIR/launch/slam_sim_launch.py simulation_config_file:=$CONFIG_FILE"

open_window 2 "Platform" \
  "$SOURCE_CMD && sleep 5 && ros2 launch as2_platform_gazebo platform_gazebo_launch.py namespace:=$NAMESPACE simulation_config_file:=$CONFIG_FILE create_bridges:=false platform_config_file:=$AS2_CONFIG"

open_window 3 "StateEstimator" \
  "$SOURCE_CMD && sleep 7 && ros2 launch as2_state_estimator state_estimator_launch.py namespace:=$NAMESPACE plugin_name:=ground_truth config_file:=$AS2_CONFIG"

open_window 4 "Controller" \
  "$SOURCE_CMD && sleep 8 && ros2 launch as2_motion_controller controller_launch.py namespace:=$NAMESPACE plugin_name:=pid_speed_controller config_file:=$AS2_CONFIG plugin_config_file:=$CONTROLLER_CONFIG"

open_window 5 "Behaviors" \
  "$SOURCE_CMD && sleep 9 && ros2 launch as2_behaviors_motion motion_behaviors_launch.py namespace:=$NAMESPACE use_sim_time:=true config_file:=$BEHAVIORS_CONFIG"

open_window 6 "SLAM" \
  "$SOURCE_CMD && sleep 10 && ros2 launch as2_slam_wrapper slam_wrapper_launch.py namespace:=$NAMESPACE use_sim_time:=true config_file:=$SLAM_CONFIG"

open_window 7 "RViz" \
  "$SOURCE_CMD && sleep 12 && rviz2 -d $RVIZ_FILE"

open_window 8 "MapManager" \
  "$SOURCE_CMD && sleep 11 && ros2 launch as2_3d_map_manager map_manager_launch.py namespace:=$NAMESPACE use_sim_time:=true config_file:=$MAP_MANAGER_CONFIG"

open_window 9 "Teleop" \
  "$SOURCE_CMD && sleep 14 && python3 -m as2_keyboard_teleoperation.keyboard_teleoperation \
      --namespace $NAMESPACE \
      --use_sim_time true \
      --verbose false \
      --speed_value 1.0 \
      --altitude_speed_value 0.5 \
      --turn_speed_value 0.5 \
      --position_value 1.0 \
      --altitude_value 2.0 \
      --turn_angle_value 0.5 \
      --speed_frame_id base_link \
      --pose_frame_id earth \
      --initial_mode pose"

cat <<EOF
[$TEST_NAME] 9 pencere açıldı.
  Sıralama: Sim → Platform → StateEstimator → Controller → Behaviors → SLAM → RViz → MapManager → Teleop
  Loglar: $LOG_DIR/
  Kapatmak için: $SCRIPT_DIR/stop.sh
EOF
