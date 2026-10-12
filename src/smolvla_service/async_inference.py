"""Single-flight inference used by the ROS node without blocking callbacks."""

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock


class AsyncInference:
    def __init__(self, policy):
        self._policy = policy
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="smolvla")
        self._future: Future | None = None
        self._lock = Lock()

    def submit(self, observation) -> bool:
        """Submit only when no inference is running or waiting to be consumed."""
        with self._lock:
            if self._future is not None:
                return False
            self._future = self._executor.submit(self._policy, observation)
            return True

    def poll(self):
        """Return a completed action once; return None while idle or running."""
        with self._lock:
            if self._future is None or not self._future.done():
                return None
            future, self._future = self._future, None
        return future.result()

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._future is not None

    def close(self):
        self._executor.shutdown(wait=True, cancel_futures=True)
