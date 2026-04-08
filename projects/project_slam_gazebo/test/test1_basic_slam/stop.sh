#!/usr/bin/env bash
# test1_basic_slam/stop.sh — test1 süreçlerini ve pencerelerini kapat
set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_NAME="test1"
source "$SCRIPT_DIR/../_common.sh"
stop_all
