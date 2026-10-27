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


def test_reset_waits_for_stale_inference_then_clears_policy_state():
    release = threading.Event()
    started = threading.Event()

    class StatefulPolicy:
        def __init__(self):
            self.values = []
            self.reset_calls = 0

        def __call__(self, value):
            started.set()
            release.wait(timeout=2)
            self.values.append(value)
            return [value] * 7

        def reset(self):
            self.values.clear()
            self.reset_calls += 1

    policy = StatefulPolicy()
    runner = AsyncInference(policy)
    reset_thread = None
    try:
        assert runner.submit("stale")
        assert started.wait(timeout=1)
        reset_thread = threading.Thread(target=runner.reset)
        reset_thread.start()
        time.sleep(0.01)
        assert reset_thread.is_alive()

        release.set()
        reset_thread.join(timeout=1)
        assert not reset_thread.is_alive()
        assert policy.reset_calls == 1
        assert policy.values == []
        assert runner.poll() is None
    finally:
        release.set()
        if reset_thread is not None:
            reset_thread.join(timeout=1)
        runner.close()
