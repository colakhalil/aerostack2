#!/usr/bin/env bash
# test2_obstacle_slam/stop.sh — test2 süreçlerini ve pencerelerini kapat
set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_NAME="test2"
source "$SCRIPT_DIR/../_common.sh"
stop_all
