"""Expose one LIBERO environment as a ROS2 action/observation loop."""

import numpy as np
import rclpy
from lerobot.envs.libero import LiberoEnv
from lerobot.envs.utils import preprocess_observation
from lerobot.processor.env_processor import LiberoProcessorStep
from libero.libero import benchmark
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray


def image_message(node, image):
    image = np.ascontiguousarray(image, dtype=np.uint8)
    msg = Image()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.height, msg.width = image.shape[:2]
    msg.encoding = "rgb8"
    msg.is_bigendian = False
    msg.step = msg.width * 3
    msg.data = image.tobytes()
    return msg


class SimNode(Node):
    def __init__(self):
        super().__init__("libero_sim")
        self.declare_parameter("suite", "libero_object")
        self.declare_parameter("task_id", 0)
        self.declare_parameter("init_state", 0)
        self.declare_parameter("max_actions", 280)
        self.declare_parameter("stop_after_episode", False)
        suite_name = self.get_parameter("suite").value
        task_id = int(self.get_parameter("task_id").value)
        init_state = int(self.get_parameter("init_state").value)
        self.max_actions = int(self.get_parameter("max_actions").value)
        self.stop_after_episode = bool(self.get_parameter("stop_after_episode").value)
        self.action_count = 0
        suite = benchmark.get_benchmark_dict()[suite_name]()
        self.env = LiberoEnv(
            task_suite=suite,
            task_id=task_id,
            task_suite_name=suite_name,
            obs_type="pixels_agent_pos",
            episode_index=init_state,
            observation_width=256,
            observation_height=256,
        )
        self.task = suite.get_task(task_id).language
        self.state_processor = LiberoProcessorStep()
        self.camera = self.create_publisher(Image, "/camera/image_raw", 1)
        self.wrist = self.create_publisher(Image, "/camera/wrist/image_raw", 1)
        self.state = self.create_publisher(Float32MultiArray, "/robot_state", 1)
        self.create_subscription(Float32MultiArray, "/vla/action", self.on_action, 1)
        observation, _ = self.env.reset(seed=init_state)
        self.publish_observation(observation)

    def publish_observation(self, observation):
        self.camera.publish(image_message(self, observation["pixels"]["image"]))
        self.wrist.publish(image_message(self, observation["pixels"]["image2"]))
        tensor_obs = preprocess_observation(observation)
        # LiberoProcessorStep is normally fed by a vector env. Add that missing
        # batch dimension to each field from this direct single environment.
        robot_state = tensor_obs.get("observation.robot_state", {})
        for component in robot_state.values():
            for name, value in component.items():
                if value.ndim == 1:
                    component[name] = value.unsqueeze(0)
        tensor_obs = self.state_processor.observation(tensor_obs)
        values = tensor_obs["observation.state"][0].cpu().numpy().astype(np.float32)
        self.state.publish(Float32MultiArray(data=values.tolist()))

    def on_action(self, message):
        action = np.asarray(message.data, dtype=np.float32)
        if action.shape != (7,) or not np.isfinite(action).all():
            self.get_logger().error("Ignoring action: expected seven finite values")
            return
        observation, _, terminated, _, info = self.env.step(action)
        self.action_count += 1
        success = bool(info.get("is_success", False))
        finished = terminated or success or self.action_count >= self.max_actions
        if finished:
            self.get_logger().info(
                f"ROS2_EPISODE_RESULT success={success} actions={self.action_count}"
            )
            if self.stop_after_episode:
                rclpy.shutdown()
                return
            observation, _ = self.env.reset()
            self.action_count = 0
        self.publish_observation(observation)

    def destroy_node(self):
        self.env.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = SimNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
