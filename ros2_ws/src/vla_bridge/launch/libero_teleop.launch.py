from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default = Path(get_package_share_directory("vla_bridge")) / "config/libero_object_teleop.yaml"
    config = LaunchConfiguration("config")
    sim = Node(package="vla_bridge", executable="sim_node", parameters=[config], output="screen")
    teleop = Node(
        package="vla_bridge",
        executable="web_teleop_node",
        parameters=[config],
        output="screen",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument("config", default_value=str(default)),
            sim,
            teleop,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=sim,
                    on_exit=[EmitEvent(event=Shutdown(reason="LIBERO sim stopped"))],
                )
            ),
        ]
    )
