"""Helpers for assembling one coherent camera/state observation."""

INPUT_KEYS = ("camera", "wrist", "state")


def fresh_synchronized_snapshot(inputs, now, timeout_s, tolerance_s):
    """Return a bundle and its source entries, or ``(None, None)``.

    Each mapping value is ``(payload, monotonic_receive_time)``.  Requiring all
    receive times to be close prevents mixing cameras and robot state from
    adjacent simulator steps.
    """
    if not all(key in inputs for key in INPUT_KEYS):
        return None, None
    snapshot = {key: inputs[key] for key in INPUT_KEYS}
    timestamps = [value[1] for value in snapshot.values()]
    if any(now - timestamp > timeout_s for timestamp in timestamps):
        return None, None
    if max(timestamps) - min(timestamps) > tolerance_s:
        return None, None
    return tuple(snapshot[key][0] for key in INPUT_KEYS), snapshot
