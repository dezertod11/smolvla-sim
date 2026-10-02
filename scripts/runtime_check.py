"""Check CUDA, GPU EGL rendering, quantization kernels and ROS2 in the runtime."""

import argparse
import importlib.metadata
import json
import os
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ros", action="store_true")
    args = parser.parse_args()
    import numpy as np
    import torch

    versions = {}
    for name in ["torch", "torchvision", "torchcodec", "lerobot", "mujoco", "bitsandbytes"]:
        versions[name] = importlib.metadata.version(name)
    print(json.dumps(versions, indent=2), flush=True)
    assert torch.cuda.is_available(), "CUDA is unavailable"
    x = torch.randn(64, 64, device="cuda", requires_grad=True)
    (x @ x).square().mean().backward()
    torch.cuda.synchronize()
    print("PASS CUDA forward/backward:", torch.cuda.get_device_name(0), flush=True)

    import bitsandbytes as bnb

    linear = bnb.nn.Linear8bitLt(64, 32, has_fp16_weights=False).cuda()
    result = linear(torch.randn(2, 64, device="cuda", dtype=torch.float16))
    torch.cuda.synchronize()
    assert torch.isfinite(result).all()
    print("PASS bitsandbytes INT8 CUDA kernel", flush=True)

    import mujoco
    from OpenGL import GL

    model = mujoco.MjModel.from_xml_string(
        '<mujoco><worldbody><light pos="0 0 3"/><geom type="sphere" size=".2"/>'
        '</worldbody></mujoco>'
    )
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    with mujoco.Renderer(model, height=128, width=128) as renderer:
        renderer.update_scene(data)
        pixels = renderer.render()
        renderer_name = GL.glGetString(GL.GL_RENDERER).decode()
        assert pixels.shape == (128, 128, 3) and np.std(pixels) > 1
        assert "llvmpipe" not in renderer_name.lower(), renderer_name
        print("PASS MuJoCo EGL frame:", renderer_name, flush=True)

    if not args.skip_ros:
        import rclpy
        from std_msgs.msg import Float32MultiArray

        os.environ.setdefault("ROS_DOMAIN_ID", "73")
        os.environ.setdefault("ROS_AUTOMATIC_DISCOVERY_RANGE", "LOCALHOST")
        rclpy.init()
        publisher_node = rclpy.create_node("robotics_setup_publisher")
        subscriber_node = rclpy.create_node("robotics_setup_subscriber")
        received = []
        topic = f"/robotics_setup_check_{os.getpid()}"
        sub = subscriber_node.create_subscription(
            Float32MultiArray, topic, lambda msg: received.append(list(msg.data)), 10
        )
        pub = publisher_node.create_publisher(Float32MultiArray, topic, 10)
        deadline = time.monotonic() + 10
        while not received and time.monotonic() < deadline:
            pub.publish(Float32MultiArray(data=[0.0] * 7))
            rclpy.spin_once(subscriber_node, timeout_sec=0.1)
        assert received and len(received[0]) == 7, "ROS2 pub/sub timeout"
        subscriber_node.destroy_subscription(sub)
        publisher_node.destroy_node()
        subscriber_node.destroy_node()
        rclpy.shutdown()
        print("PASS ROS2 Jazzy two-node pub/sub", flush=True)


if __name__ == "__main__":
    main()
