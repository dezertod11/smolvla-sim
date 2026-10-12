import threading
import time

from smolvla_service.async_inference import AsyncInference


def test_single_flight_does_not_block_caller():
    release = threading.Event()
    started = threading.Event()

    def policy(value):
        started.set()
        release.wait(timeout=2)
        return [value] * 7

    runner = AsyncInference(policy)
    try:
        assert runner.submit(3)
        assert started.wait(timeout=1)
        assert runner.busy
        assert not runner.submit(4)
        assert runner.poll() is None
        release.set()
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            action = runner.poll()
            if action is not None:
                break
            time.sleep(0.001)
        assert action == [3] * 7
        assert not runner.busy
    finally:
        release.set()
        runner.close()


def test_policy_error_surfaces_on_poll():
    runner = AsyncInference(lambda _: 1 / 0)
    try:
        assert runner.submit(None)
        deadline = time.monotonic() + 1
        while runner.busy and time.monotonic() < deadline:
            try:
                result = runner.poll()
            except ZeroDivisionError:
                break
            if result is None:
                time.sleep(0.001)
                continue
        else:
            raise AssertionError("Expected policy error")
    finally:
        runner.close()
