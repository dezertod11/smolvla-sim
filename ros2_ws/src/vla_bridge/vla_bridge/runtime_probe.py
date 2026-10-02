"""Bounded checks of the installed ROS2 package and message transport."""

import time

import rclpy
from std_msgs.msg import Float32MultiArray


def publisher():
    rclpy.init()
    node = rclpy.create_node("smolvla_setup_publisher")
    pub = node.create_publisher(Float32MultiArray, "/smolvla_setup/action", 10)
    timer = node.create_timer(0.1, lambda: pub.publish(Float32MultiArray(data=[0.0] * 7)))
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_timer(timer)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def subscriber():
    rclpy.init()
    node = rclpy.create_node("smolvla_setup_subscriber")
    received = []
    node.create_subscription(
        Float32MultiArray, "/smolvla_setup/action", lambda msg: received.append(msg.data), 10
    )
    deadline = time.monotonic() + 15
    try:
        while not received and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if not received or len(received[0]) != 7:
            raise RuntimeError("ROS2 action transport timed out or returned a wrong shape")
        node.get_logger().info("PASS: received seven action values between ROS2 processes")
    finally:
        node.destroy_node()
        rclpy.shutdown()
