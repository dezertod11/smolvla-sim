import json

from scripts.eval_managed import checkpoint_rename_map
from scripts.run_final_bundle import command


def test_own_checkpoint_gets_environment_camera_rename(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({
        "input_features": {"observation.images.camera1": {},
                           "observation.images.camera2": {}},
    }))
    assert checkpoint_rename_map(tmp_path) == {
        "observation.images.image": "observation.images.camera1",
        "observation.images.image2": "observation.images.camera2",
    }


def test_bundle_builds_bounded_argv(tmp_path):
    argv = command("eval-int8-n10", tmp_path / "model", tmp_path, tmp_path / "out")
    assert argv[1].endswith("eval_managed.py")
    assert argv[-2:] == ["--precision", "int8"]
