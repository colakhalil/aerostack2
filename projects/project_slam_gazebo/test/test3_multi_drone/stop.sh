#!/usr/bin/env bash
# test3_multi_drone/stop.sh — test3 süreçlerini ve pencerelerini kapat
set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_NAME="test3"
source "$SCRIPT_DIR/../_common.sh"

# _common.sh stop_all 9 pencereye kadar kapatıyor, 16'ya genişlet
stop_all

# 10-17 arası pencereleri de kapat
if command -v wmctrl &>/dev/null; then
  for n in 10 11 12 13 14 15 16 17; do
    wmctrl -c "${TEST_NAME}-${n}-" 2>/dev/null
  done
fi
