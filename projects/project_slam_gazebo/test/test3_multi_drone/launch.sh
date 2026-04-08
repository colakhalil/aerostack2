#!/usr/bin/env bash
# test3_multi_drone/launch.sh — 2 drone + SLAM + MapManager testi
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_NAME="test3"
source "$SCRIPT_DIR/../_common.sh"

CONFIG_FILE="$PROJECT_DIR/config/slam_multi.json"
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config bulunamadı: $CONFIG_FILE"; exit 1
fi

RVIZ_TEST3="$SCRIPT_DIR/rviz_test3.rviz"
rm -f "$LOG_DIR"/${TEST_NAME}_t*.log

echo "[$TEST_NAME] Multi-drone stack başlatılıyor (2 drone)"
echo "[$TEST_NAME] Loglar: $LOG_DIR/"

# ─── T1: Gazebo (ortak, 2 drone spawn) ───
open_window 1 "Sim" \
  "$SOURCE_CMD && ros2 launch $PROJECT_DIR/launch/slam_sim_launch.py simulation_config_file:=$CONFIG_FILE"

# ─── drone0 stack (T2-T7) ───
NS0="drone0"

open_window 2 "D0-Platform" \
  "$SOURCE_CMD && sleep 5 && ros2 launch as2_platform_gazebo platform_gazebo_launch.py namespace:=$NS0 simulation_config_file:=$CONFIG_FILE create_bridges:=false platform_config_file:=$AS2_CONFIG"

open_window 3 "D0-StateEst" \
  "$SOURCE_CMD && sleep 7 && ros2 launch as2_state_estimator state_estimator_launch.py namespace:=$NS0 plugin_name:=ground_truth config_file:=$AS2_CONFIG"

open_window 4 "D0-Controller" \
  "$SOURCE_CMD && sleep 8 && ros2 launch as2_motion_controller controller_launch.py namespace:=$NS0 plugin_name:=pid_speed_controller config_file:=$AS2_CONFIG plugin_config_file:=$CONTROLLER_CONFIG"

open_window 5 "D0-Behaviors" \
  "$SOURCE_CMD && sleep 9 && ros2 launch as2_behaviors_motion motion_behaviors_launch.py namespace:=$NS0 use_sim_time:=true config_file:=$BEHAVIORS_CONFIG"

open_window 6 "D0-SLAM" \
  "$SOURCE_CMD && sleep 10 && ros2 launch as2_slam_wrapper slam_wrapper_launch.py namespace:=$NS0 use_sim_time:=true config_file:=$SLAM_CONFIG"

open_window 7 "D0-MapMgr" \
  "$SOURCE_CMD && sleep 11 && ros2 launch as2_3d_map_manager map_manager_launch.py namespace:=$NS0 use_sim_time:=true config_file:=$MAP_MANAGER_CONFIG output_dir:=$MAPS_DIR"

# ─── drone1 stack (T8-T13) ───
NS1="drone1"

open_window 8 "D1-Platform" \
  "$SOURCE_CMD && sleep 5 && ros2 launch as2_platform_gazebo platform_gazebo_launch.py namespace:=$NS1 simulation_config_file:=$CONFIG_FILE create_bridges:=false platform_config_file:=$AS2_CONFIG"

open_window 9 "D1-StateEst" \
  "$SOURCE_CMD && sleep 7 && ros2 launch as2_state_estimator state_estimator_launch.py namespace:=$NS1 plugin_name:=ground_truth config_file:=$AS2_CONFIG"

open_window 10 "D1-Controller" \
  "$SOURCE_CMD && sleep 8 && ros2 launch as2_motion_controller controller_launch.py namespace:=$NS1 plugin_name:=pid_speed_controller config_file:=$AS2_CONFIG plugin_config_file:=$CONTROLLER_CONFIG"

open_window 11 "D1-Behaviors" \
  "$SOURCE_CMD && sleep 9 && ros2 launch as2_behaviors_motion motion_behaviors_launch.py namespace:=$NS1 use_sim_time:=true config_file:=$BEHAVIORS_CONFIG"

open_window 12 "D1-SLAM" \
  "$SOURCE_CMD && sleep 10 && ros2 launch as2_slam_wrapper slam_wrapper_launch.py namespace:=$NS1 use_sim_time:=true config_file:=$SLAM_CONFIG"

open_window 13 "D1-MapMgr" \
  "$SOURCE_CMD && sleep 11 && ros2 launch as2_3d_map_manager map_manager_launch.py namespace:=$NS1 use_sim_time:=true config_file:=$MAP_MANAGER_CONFIG output_dir:=$MAPS_DIR"

# ─── T14: Map Merger ───
open_window 14 "MapMerger" \
  "$SOURCE_CMD && sleep 12 && ros2 launch as2_3d_map_manager map_merger_launch.py use_sim_time:=true output_dir:=$MAPS_DIR"

# ─── T15: RViz (ortak) ───
RVIZ_TEST3="$SCRIPT_DIR/rviz_test3.rviz"
open_window 15 "RViz" \
  "$SOURCE_CMD && sleep 13 && rviz2 -d $RVIZ_TEST3"

# ─── T16-T17: Teleop (her drone için ayrı) ───
open_window 16 "D0-Teleop" \
  "$SOURCE_CMD && sleep 15 && python3 -m as2_keyboard_teleoperation.keyboard_teleoperation \
      --namespace $NS0 \
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

open_window 17 "D1-Teleop" \
  "$SOURCE_CMD && sleep 15 && python3 -m as2_keyboard_teleoperation.keyboard_teleoperation \
      --namespace $NS1 \
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
[$TEST_NAME] 17 pencere açıldı (2 drone + map merger).
  drone0: T2-T7 (Platform, StateEst, Controller, Behaviors, SLAM, MapMgr)
  drone1: T8-T13 (aynı stack)
  Ortak:  T1=Sim, T14=MapMerger, T15=RViz, T16=D0-Teleop, T17=D1-Teleop
  Loglar: $LOG_DIR/
  Kapatmak için: $SCRIPT_DIR/stop.sh

  Teleop: drone0=T16, drone1=T17
  Merged map kaydet: ros2 service call /map_merger/save_map std_srvs/srv/Trigger
EOF
