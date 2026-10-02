from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node


def generate_launch_description():
    pub = Node(package="vla_bridge", executable="runtime_publisher", output="screen")
    sub = Node(package="vla_bridge", executable="runtime_subscriber", output="screen")
    return LaunchDescription([
        pub,
        sub,
        RegisterEventHandler(OnProcessExit(
            target_action=sub,
            on_exit=[EmitEvent(event=Shutdown(reason="Runtime check completed"))],
        )),
    ])
