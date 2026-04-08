#!/usr/bin/env bash
# _common.sh — Tüm testlerin paylaştığı ortak değişkenler ve fonksiyonlar.
# Doğrudan çalıştırılmaz, test scriptleri tarafından source edilir.

# Çağıran script'in SCRIPT_DIR ve TEST_NAME değişkenlerini set etmesi gerekir.
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE_DIR="$(cd "$PROJECT_DIR/../.." && pwd)"

NAMESPACE="drone0"
RVIZ_FILE="$PROJECT_DIR/rviz/slam_lidar.rviz"
SLAM_CONFIG="$WORKSPACE_DIR/install/as2_slam_wrapper/share/as2_slam_wrapper/config/slam_wrapper_config.yaml"
MAP_MANAGER_CONFIG="$WORKSPACE_DIR/install/as2_3d_map_manager/share/as2_3d_map_manager/config/map_manager_config.yaml"
AS2_CONFIG="$PROJECT_DIR/config/as2_config.yaml"
BEHAVIORS_CONFIG="$PROJECT_DIR/config/behaviors_config.yaml"
CONTROLLER_CONFIG="$PROJECT_DIR/config/controller_pid_config.yaml"

SOURCE_CMD="source /opt/ros/humble/setup.bash && source $WORKSPACE_DIR/install/setup.bash"

# Log klasörü — her testin kendi logs/ dizini
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Yeni gnome-terminal penceresi açan helper
# $1: pencere numarası, $2: başlık, $3: shell komutu
open_window() {
  local n="$1"
  local title="$2"
  local cmd="$3"
  local logfile="$LOG_DIR/${TEST_NAME}_t${n}.log"
  gnome-terminal --window --title="${TEST_NAME}-${n}-${title}" -- bash -c \
    "$cmd 2>&1 | stdbuf -oL -eL tee '$logfile'; echo; echo '[exited — press enter to close]'; read" &
  sleep 0.3
}

# Tüm süreçleri temiz kapatma
stop_all() {
  echo "[$TEST_NAME-stop] Süreçler kapatılıyor..."
  pkill -f "as2_keyboard_teleoperation"  2>/dev/null
  pkill -f "slam_wrapper_py"             2>/dev/null
  pkill -f "as2_3d_map_manager"          2>/dev/null
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

  # gnome-terminal pencerelerini kapat (wmctrl varsa)
  if command -v wmctrl &>/dev/null; then
    for n in 1 2 3 4 5 6 7 8 9; do
      wmctrl -c "${TEST_NAME}-${n}-" 2>/dev/null
    done
  else
    echo "[$TEST_NAME-stop] wmctrl yok, terminal pencereleri manuel kapatılmalı (sudo apt install wmctrl)"
  fi
  echo "[$TEST_NAME-stop] Bitti."
}
