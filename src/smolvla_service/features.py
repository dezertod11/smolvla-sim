"""Feature-name adapters shared by evaluation, benchmarks, and ROS2."""


def camera_rename_map(input_features):
    if "observation.images.camera1" not in input_features:
        return {}
    return {
        "observation.images.image": "observation.images.camera1",
        "observation.images.image2": "observation.images.camera2",
    }
