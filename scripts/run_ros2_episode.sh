#!/usr/bin/env bash
set -euo pipefail
config=${1:?Pass a ROS2 parameter YAML file}
cd "$(dirname "$0")/../ros2_ws"
set +u
source /opt/ros/jazzy/setup.bash
set -u
python -m colcon build --symlink-install --packages-select vla_bridge
set +u
source install/setup.bash
set -u
log=$(mktemp)
trap 'rm -f "$log"' EXIT
set +e
ros2 launch vla_bridge libero_smolvla.launch.py config:="$config" 2>&1 | tee "$log"
launch_status=${PIPESTATUS[0]}
set -e
test "$launch_status" -eq 0 || exit "$launch_status"
grep -q "ROS2_EPISODE_RESULT" "$log" || {
  echo "ROS2 launch stopped without an episode result" >&2
  exit 1
}
