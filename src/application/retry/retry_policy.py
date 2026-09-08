import time
from typing import Any, Callable


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int,
        delay_seconds: float,
        backoff_multiplier: float,
        wait: Callable[[float], None] | None = None,
    ):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero")

        if delay_seconds < 0:
            raise ValueError("delay_seconds must be greater than or equal to zero")

        if backoff_multiplier <= 0:
            raise ValueError("backoff_multiplier must be greater than zero")

        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self._wait = wait or time.sleep

    def execute(self, operation: Callable[[], Any]) -> Any:
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return operation()
            except Exception as exc:
                last_exception = exc

                if attempt == self.max_attempts - 1:
                    raise

                delay = (
                    self.delay_seconds
                    * (self.backoff_multiplier ** attempt)
                )

                if delay > 0:
                    self._wait(delay)

        raise last_exception
