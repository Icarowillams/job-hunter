from threading import Event
from unittest.mock import Mock

from src.application.scheduler import ApplicationScheduler


def test_scheduler_runs_application_once():
    runner = Mock()
    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
    )

    scheduler.run_once()

    runner.run_once.assert_called_once_with()


def test_scheduler_uses_configured_interval():
    runner = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=120,
    )

    assert scheduler.interval_seconds == 120


def test_scheduler_can_be_stopped():
    runner = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
    )

    scheduler.stop()

    assert scheduler.is_running is False


def test_scheduler_start_runs_application():
    runner = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
    )

    scheduler.start()

    runner.run_once.assert_called_once_with()

    scheduler.stop()


def test_scheduler_start_sets_running_state():
    runner = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
    )

    scheduler.start()

    assert scheduler.is_running is True

    scheduler.stop()


def test_scheduler_stop_sets_running_state_to_false():
    runner = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
    )

    scheduler.start()
    scheduler.stop()

    assert scheduler.is_running is False


def test_scheduler_does_not_start_twice():
    runner = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
    )

    scheduler.start()
    scheduler.start()

    assert runner.run_once.call_count == 1

    scheduler.stop()


def test_scheduler_waits_between_executions():
    runner = Mock()
    wait = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
        wait=wait,
    )

    scheduler.start()

    assert wait.called
    assert wait.call_args.args[0] == 60

    scheduler.stop()


def test_scheduler_stops_after_wait_requests_stop():
    runner = Mock()
    wait = Mock()

    scheduler = None

    def stop_after_wait(seconds):
        scheduler.stop()

    wait.side_effect = stop_after_wait

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
        wait=wait,
    )

    scheduler.start()

    assert runner.run_once.call_count == 1
    assert scheduler.is_running is False


def test_scheduler_uses_interruptible_stop_event_when_no_custom_wait():
    runner = Mock()

    scheduler = ApplicationScheduler(
        runner=runner,
        interval_seconds=60,
    )

    assert isinstance(scheduler._stop_event, Event)

    scheduler.stop()

    assert scheduler._stop_event.is_set() is True
