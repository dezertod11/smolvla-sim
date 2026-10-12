"""Reset, step and render an actual LIBERO task using both policy cameras."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    from configure_libero import configure

    configure()
    import imageio.v3 as iio
    import numpy as np
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    from OpenGL import GL

    suite = benchmark.get_benchmark_dict()["libero_object"]()
    task = suite.get_task(0)
    bddl = Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
    env = OffScreenRenderEnv(
        bddl_file_name=str(bddl), camera_heights=256, camera_widths=256
    )
    output = args.output or Path(
        os.environ.get("ROBOTICS_OUTPUT_DIR", "/data/checks/libero")
    )
    output.mkdir(parents=True, exist_ok=True)
    try:
        env.seed(0)
        obs = env.reset()
        obs = env.set_init_state(suite.get_task_init_states(0)[0])
        for _ in range(10):
            obs, _, _, _ = env.step(np.zeros(7))
        for name in ["agentview_image", "robot0_eye_in_hand_image"]:
            frame = obs[name]
            assert frame.shape == (256, 256, 3) and np.std(frame) > 1
            iio.imwrite(output / f"{name}.png", frame)
        result = {
            "status": "pass",
            "task": task.language,
            "renderer": GL.glGetString(GL.GL_RENDERER).decode(),
            "cameras": ["agentview_image", "robot0_eye_in_hand_image"],
            "note": "Environment smoke test, not a policy success-rate measurement",
        }
        (output / "result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2), flush=True)
    finally:
        env.close()


if __name__ == "__main__":
    main()
