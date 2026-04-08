#!/usr/bin/env bash
# test1_full_stack_launch.sh
# SLAM test stack'ini AYRI gnome-terminal pencerelerinde başlatır.
# Her pencerenin çıktısı test/terminal_logs/test1_terminal<N>.log dosyasına yazılır.
#
# Mimariyi değiştirmez: her pencere standart AS2 launch dosyasını çağırır.
#
# Kullanım:
#   ./test1_full_stack_launch.sh                 # default: slam_single
#   ./test1_full_stack_launch.sh slam_obstacle   # engelli dünya

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_DIR="$(cd "$PROJECT_DIR/../.." && pwd)"

CONFIG_NAME="${1:-slam_single}"
CONFIG_FILE="$PROJECT_DIR/config/${CONFIG_NAME}.json"
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config bulunamadı: $CONFIG_FILE"
  exit 1
fi

NAMESPACE="drone0"
RVIZ_FILE="$PROJECT_DIR/rviz/slam_lidar.rviz"
SLAM_CONFIG="$WORKSPACE_DIR/install/as2_slam_wrapper/share/as2_slam_wrapper/config/slam_wrapper_config.yaml"
AS2_CONFIG="$PROJECT_DIR/config/as2_config.yaml"
BEHAVIORS_CONFIG="$PROJECT_DIR/config/behaviors_config.yaml"
CONTROLLER_CONFIG="$PROJECT_DIR/config/controller_pid_config.yaml"

# Log klasörü — eski logları temizle
LOG_DIR="$SCRIPT_DIR/terminal_logs"
mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/test1_terminal*.log

SOURCE_CMD="source /opt/ros/humble/setup.bash && source $WORKSPACE_DIR/install/setup.bash"

# Yeni gnome-terminal penceresi açan helper
# $1: pencere numarası, $2: başlık, $3: shell komutu
open_window() {
  local n="$1"
  local title="$2"
  local cmd="$3"
  local logfile="$LOG_DIR/test1_terminal${n}.log"
  # stdbuf: line-buffered, böylece log dosyası gerçek zamanlı dolar
  gnome-terminal --window --title="${n}-${title}" -- bash -c \
    "$cmd 2>&1 | stdbuf -oL -eL tee '$logfile'; echo; echo '[exited — press enter to close]'; read" &
  sleep 0.3
}

echo "[test1] SLAM stack başlatılıyor — config: $CONFIG_NAME"
echo "[test1] Loglar: $LOG_DIR/test1_terminal{1..8}.log"

# 1) Gazebo + dünya + bridges (slam_sim_launch.py zaten drone_bridges kurar)
open_window 1 "Sim" \
  "$SOURCE_CMD && ros2 launch $PROJECT_DIR/launch/slam_sim_launch.py simulation_config_file:=$CONFIG_FILE"

# 2) Aerial platform — create_bridges:=false (T1 zaten kurdu), birleşik config
open_window 2 "Platform" \
  "$SOURCE_CMD && sleep 5 && ros2 launch as2_platform_gazebo platform_gazebo_launch.py namespace:=$NAMESPACE simulation_config_file:=$CONFIG_FILE create_bridges:=false platform_config_file:=$AS2_CONFIG"

# 3) State estimator (ground_truth) — birleşik config
open_window 3 "StateEstimator" \
  "$SOURCE_CMD && sleep 7 && ros2 launch as2_state_estimator state_estimator_launch.py namespace:=$NAMESPACE plugin_name:=ground_truth config_file:=$AS2_CONFIG"

# 4) Motion controller — birleşik config
open_window 4 "Controller" \
  "$SOURCE_CMD && sleep 8 && ros2 launch as2_motion_controller controller_launch.py namespace:=$NAMESPACE plugin_name:=pid_speed_controller config_file:=$AS2_CONFIG plugin_config_file:=$CONTROLLER_CONFIG"

# 5) Motion behaviors — birleşik config tüm 4 behavior için
open_window 5 "Behaviors" \
  "$SOURCE_CMD && sleep 9 && ros2 launch as2_behaviors_motion motion_behaviors_launch.py namespace:=$NAMESPACE use_sim_time:=true config_file:=$BEHAVIORS_CONFIG"

# 6) SLAM wrapper (KISS-ICP)
open_window 6 "SLAM" \
  "$SOURCE_CMD && sleep 10 && ros2 launch as2_slam_wrapper slam_wrapper_launch.py namespace:=$NAMESPACE use_sim_time:=true config_file:=$SLAM_CONFIG"

# 7) RViz
open_window 7 "RViz" \
  "$SOURCE_CMD && sleep 12 && rviz2 -d $RVIZ_FILE"

# 8) Klavye teleop — paket executable kurmuyor, python modülü olarak çağır
#    Argparse default'ları None olduğu için TÜM argümanları açıkça vermek gerekiyor
open_window 8 "Teleop" \
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
[test1] 8 pencere açıldı.
  Sıralama: Sim → Platform → StateEstimator → Controller → Behaviors → SLAM → RViz → Teleop
  Her pencerenin canlı log dosyası: $LOG_DIR/test1_terminal<N>.log
  Kapatmak için: ./test1_full_stack_stop.sh
EOF
