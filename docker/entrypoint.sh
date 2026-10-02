#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
if test -f /workspace/ros2_ws/install/setup.bash; then
  source /workspace/ros2_ws/install/setup.bash
fi
exec "$@"
