#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../ros2_ws"
set +u
source /opt/ros/jazzy/setup.bash
set -u
python -m colcon build --symlink-install --packages-select vla_bridge
set +u
source install/setup.bash
set -u
ros2 launch vla_bridge libero_teleop.launch.py
