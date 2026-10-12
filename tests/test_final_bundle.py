from scripts.run_final_bundle import command
from smolvla_service.features import camera_rename_map


def test_own_checkpoint_gets_environment_camera_rename():
    assert camera_rename_map({
        "observation.images.camera1": {}, "observation.images.camera2": {}
    }) == {
        "observation.images.image": "observation.images.camera1",
        "observation.images.image2": "observation.images.camera2",
    }


def test_bundle_builds_bounded_argv(tmp_path):
    argv = command("eval-int8-n10", tmp_path / "model", tmp_path, tmp_path / "out")
    assert argv[1].endswith("eval_managed.py")
    assert argv[-2:] == ["--precision", "int8"]
