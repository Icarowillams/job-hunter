import time
from threading import Event, Thread, current_thread
from typing import Any, Callable


class ApplicationScheduler:
    def __init__(
        self,
        runner: Any,
        interval_seconds: int,
        wait: Callable[[float], None] | None = None,
    ):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")

        self.runner = runner
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._wait = wait or time.sleep
        self._stop_event = Event()
        self._thread: Thread | None = None

    def run_once(self):
        return self.runner.run_once()

    def start(self):
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()

        self.run_once()

        self._thread = Thread(
            target=self._run_loop,
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self.is_running = False
        self._stop_event.set()

        if (
            self._thread is not None
            and self._thread is not current_thread()
        ):
            self._thread.join(timeout=1)

        self._thread = None

    def _run_loop(self):
        while self.is_running:
            self._wait(self.interval_seconds)

            if not self.is_running:
                break

            self.run_once()
