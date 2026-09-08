from threading import Event, Lock
from typing import Iterable, Any
import signal


class ShutdownManager:
    def __init__(
        self,
        scheduler: Any,
        components: Iterable[Any] | None = None,
    ):
        self.scheduler = scheduler
        self.components = list(components or [])
        self.shutdown_event = Event()
        self._lock = Lock()

    def shutdown(self) -> None:
        with self._lock:
            if self.shutdown_event.is_set():
                return

            self.shutdown_event.set()

            self.scheduler.stop()

            for component in self.components:
                stop = getattr(component, "stop", None)
                if callable(stop):
                    stop()

    def wait_for_shutdown(self, timeout: float | None = None) -> bool:
        return self.shutdown_event.wait(timeout)

    def register_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame) -> None:
        self.shutdown()
