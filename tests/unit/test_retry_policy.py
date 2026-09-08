from unittest.mock import Mock

import pytest

from src.application.retry.retry_policy import RetryPolicy


def test_retry_succeeds_on_first_attempt():
    operation = Mock(return_value="ok")

    policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=0,
        backoff_multiplier=2,
    )

    result = policy.execute(operation)

    assert result == "ok"
    assert operation.call_count == 1


def test_retry_retries_after_failure():
    operation = Mock(
        side_effect=[
            RuntimeError("temporary failure"),
            "ok",
        ]
    )

    policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=0,
        backoff_multiplier=2,
    )

    result = policy.execute(operation)

    assert result == "ok"
    assert operation.call_count == 2


def test_retry_stops_after_max_attempts():
    operation = Mock(
        side_effect=RuntimeError("permanent failure")
    )

    policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=0,
        backoff_multiplier=2,
    )

    with pytest.raises(RuntimeError, match="permanent failure"):
        policy.execute(operation)

    assert operation.call_count == 3


def test_retry_uses_backoff_delay():
    operation = Mock(
        side_effect=[
            RuntimeError("temporary failure"),
            RuntimeError("temporary failure"),
            "ok",
        ]
    )

    wait = Mock()

    policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=2,
        backoff_multiplier=2,
        wait=wait,
    )

    result = policy.execute(operation)

    assert result == "ok"
    assert operation.call_count == 3

    assert wait.call_count == 2
    wait.assert_any_call(2)
    wait.assert_any_call(4)


def test_retry_does_not_wait_after_success():
    operation = Mock(
        side_effect=[
            RuntimeError("temporary failure"),
            "ok",
        ]
    )

    wait = Mock()

    policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=2,
        backoff_multiplier=2,
        wait=wait,
    )

    result = policy.execute(operation)

    assert result == "ok"
    assert wait.call_count == 1
    wait.assert_called_once_with(2)


def test_retry_validates_max_attempts():
    with pytest.raises(ValueError):
        RetryPolicy(
            max_attempts=0,
            delay_seconds=0,
            backoff_multiplier=2,
        )


def test_retry_validates_delay():
    with pytest.raises(ValueError):
        RetryPolicy(
            max_attempts=3,
            delay_seconds=-1,
            backoff_multiplier=2,
        )


def test_retry_validates_backoff_multiplier():
    with pytest.raises(ValueError):
        RetryPolicy(
            max_attempts=3,
            delay_seconds=0,
            backoff_multiplier=0,
        )
