"""Run SmolVLA asynchronously and publish seven-dimensional LIBERO actions."""

import time
from threading import Lock

import numpy as np
import rclpy
import torch
from lerobot.configs.policies import PreTrainedConfig
from lerobot.envs.configs import LiberoEnv as LiberoEnvConfig
from lerobot.envs.factory import make_env_pre_post_processors
from lerobot.envs.utils import preprocess_observation
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray

from smolvla_service.async_inference import AsyncInference
from smolvla_service.conversion import action_to_list


def decode_image(message):
    if message.encoding != "rgb8":
        raise ValueError(f"Expected rgb8 image, got {message.encoding}")
    image = np.frombuffer(message.data, dtype=np.uint8)
    return image.reshape(message.height, message.width, 3).copy()


class PolicyRunner:
    def __init__(self, checkpoint, vlm_model, task, n_action_steps, device):
        config = PreTrainedConfig.from_pretrained(checkpoint)
        if not isinstance(config, SmolVLAConfig):
            raise TypeError(f"Expected SmolVLA checkpoint, got {type(config).__name__}")
        config.device = device
        config.n_action_steps = n_action_steps
        config.pretrained_path = checkpoint
        config.vlm_model_name = vlm_model
        env_config = LiberoEnvConfig(task="libero_object", task_ids=[0])
        self.policy = make_policy(config, env_cfg=env_config).eval()
        self.env_pre, self.env_post = make_env_pre_post_processors(env_config, config)
        overrides = {
            "device_processor": {"device": device},
            "rename_observations_processor": {
                "rename_map": {
                    "observation.images.image": "observation.images.camera1",
                    "observation.images.image2": "observation.images.camera2",
                }
            },
        }
        self.pre, self.post = make_pre_post_processors(
            config, pretrained_path=checkpoint, preprocessor_overrides=overrides
        )
        self.task = task
        self.device_type = torch.device(device).type

    def __call__(self, bundle):
        camera, wrist, state = bundle
        observation = preprocess_observation(
            {"pixels": {"image": camera, "image2": wrist}, "agent_pos": state}
        )
        observation["task"] = [self.task]
        observation = self.env_pre(observation)
        observation = self.pre(observation)
        with torch.inference_mode(), torch.autocast(
            self.device_type, dtype=torch.bfloat16
        ):
            action = self.policy.select_action(observation)
        action = self.post(action)
        action = self.env_post({"action": action})["action"]
        return action_to_list(action[0].float().cpu().numpy())


class SmolVLANode(Node):
    def __init__(self):
        super().__init__("smolvla")
        self.declare_parameter("checkpoint", "/data/models/reference")
        self.declare_parameter("vlm_model", "/data/models/vlm")
        self.declare_parameter("task", "pick up the orange juice and place it in the basket")
        self.declare_parameter("n_action_steps", 10)
        self.declare_parameter("inference_hz", 10.0)
        self.declare_parameter("input_timeout_s", 2.0)
        self.declare_parameter("device", "cuda")
        checkpoint = self.get_parameter("checkpoint").value
        vlm_model = self.get_parameter("vlm_model").value
        task = self.get_parameter("task").value
        steps = int(self.get_parameter("n_action_steps").value)
        device = self.get_parameter("device").value
        self.timeout = float(self.get_parameter("input_timeout_s").value)
        self.lock = Lock()
        self.inputs = {}
        self.last_warning = 0.0
        self.publisher = self.create_publisher(Float32MultiArray, "/vla/action", 1)
        self.create_subscription(Image, "/camera/image_raw", self.on_camera, 1)
        self.create_subscription(Image, "/camera/wrist/image_raw", self.on_wrist, 1)
        self.create_subscription(Float32MultiArray, "/robot_state", self.on_state, 1)
        self.runner = AsyncInference(
            PolicyRunner(checkpoint, vlm_model, task, steps, device)
        )
        period = 1.0 / float(self.get_parameter("inference_hz").value)
        self.create_timer(period, self.tick)

    def store(self, key, value):
        with self.lock:
            self.inputs[key] = (value, time.monotonic())

    def on_camera(self, message):
        self.store("camera", decode_image(message))

    def on_wrist(self, message):
        self.store("wrist", decode_image(message))

    def on_state(self, message):
        state = np.asarray(message.data, dtype=np.float32)
        if state.shape == (8,) and np.isfinite(state).all():
            self.store("state", state.copy())
        else:
            self.get_logger().error("Ignoring robot state: expected eight finite values")

    def tick(self):
        try:
            action = self.runner.poll()
            if action is not None:
                self.publisher.publish(Float32MultiArray(data=action))
        except Exception as error:
            self.get_logger().error(f"Policy inference failed: {error}")
        now = time.monotonic()
        with self.lock:
            ready = all(key in self.inputs for key in ("camera", "wrist", "state"))
            fresh = ready and all(now - value[1] <= self.timeout for value in self.inputs.values())
            bundle = (
                tuple(self.inputs[key][0] for key in ("camera", "wrist", "state"))
                if fresh
                else None
            )
        if bundle is None:
            if now - self.last_warning >= 5.0:
                self.get_logger().warning("Waiting for fresh camera and robot-state messages")
                self.last_warning = now
            return
        self.runner.submit(bundle)

    def destroy_node(self):
        self.runner.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = SmolVLANode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
