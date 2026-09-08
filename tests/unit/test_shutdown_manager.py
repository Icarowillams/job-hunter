from threading import Event

from src.application.shutdown.shutdown_manager import ShutdownManager


class FakeScheduler:
    def __init__(self):
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1


def test_shutdown_manager_stops_scheduler():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    manager.shutdown()

    assert scheduler.stop_calls == 1


def test_shutdown_manager_is_idempotent():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    manager.shutdown()
    manager.shutdown()

    assert scheduler.stop_calls == 1


def test_shutdown_manager_sets_shutdown_event():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    manager.shutdown()

    assert manager.shutdown_event.is_set()


def test_shutdown_manager_can_wait_for_shutdown():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    manager.shutdown()

    assert manager.wait_for_shutdown(timeout=0.1) is True


def test_shutdown_manager_accepts_optional_components():
    scheduler = FakeScheduler()
    database = FakeScheduler()
    manager = ShutdownManager(
        scheduler=scheduler,
        components=[database],
    )

    manager.shutdown()

    assert scheduler.stop_calls == 1
    assert database.stop_calls == 1
import signal
from unittest.mock import Mock, patch

from src.application.shutdown.shutdown_manager import ShutdownManager


class FakeScheduler:
    def __init__(self):
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1


def test_shutdown_manager_registers_sigint_handler():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    with patch("signal.signal") as signal_mock:
        manager.register_signal_handlers()

    signal_mock.assert_any_call(
        signal.SIGINT,
        manager._handle_signal,
    )


def test_shutdown_manager_registers_sigterm_handler():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    with patch("signal.signal") as signal_mock:
        manager.register_signal_handlers()

    signal_mock.assert_any_call(
        signal.SIGTERM,
        manager._handle_signal,
    )


def test_shutdown_manager_signal_handler_triggers_shutdown():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    manager._handle_signal(signal.SIGINT, None)

    assert scheduler.stop_calls == 1
    assert manager.shutdown_event.is_set()


def test_shutdown_manager_signal_handler_is_idempotent():
    scheduler = FakeScheduler()
    manager = ShutdownManager(scheduler=scheduler)

    manager._handle_signal(signal.SIGINT, None)
    manager._handle_signal(signal.SIGTERM, None)

    assert scheduler.stop_calls == 1
