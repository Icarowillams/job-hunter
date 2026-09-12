import time
from dataclasses import dataclass
from typing import Any, Callable


class RetryExhaustedError(RuntimeError):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        original_exception: Exception,
        attempts: int,
    ):
        self.original_exception = original_exception
        self.attempts = attempts

        super().__init__(
            f"Retry exhausted after {attempts} attempts: "
            f"{original_exception}"
        )


@dataclass(frozen=True)
class RetryResult:
    value: Any
    attempts: int


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int,
        delay_seconds: float,
        backoff_multiplier: float,
        wait: Callable[[float], None] | None = None,
        on_retry: Callable[[int, Exception], None] | None = None,
    ):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero")

        if delay_seconds < 0:
            raise ValueError(
                "delay_seconds must be greater than or equal to zero"
            )

        if backoff_multiplier <= 0:
            raise ValueError(
                "backoff_multiplier must be greater than zero"
            )

        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self._wait = wait or time.sleep
        self._on_retry = on_retry

    @property
    def wait(self) -> Callable[[float], None]:
        return self._wait

    def execute(self, operation: Callable[[], Any]) -> Any:
        try:
            return self.execute_with_attempts(operation).value
        except RetryExhaustedError as exc:
            raise exc.original_exception

    def execute_with_attempts(
        self,
        operation: Callable[[], Any],
    ) -> RetryResult:
        for attempt in range(1, self.max_attempts + 1):
            try:
                value = operation()

                return RetryResult(
                    value=value,
                    attempts=attempt,
                )

            except Exception as exc:
                if attempt == self.max_attempts:
                    raise RetryExhaustedError(
                        original_exception=exc,
                        attempts=attempt,
                    ) from exc

                if self._on_retry is not None:
                    self._on_retry(attempt, exc)

                delay = self.delay_seconds * (
                    self.backoff_multiplier ** (attempt - 1)
                )

                if delay > 0:
                    self._wait(delay)

        raise RuntimeError("Retry policy exited unexpectedly")
