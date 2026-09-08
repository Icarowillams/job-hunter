from unittest.mock import Mock

from src.application.orchestrator import RunResult


def test_main_runs_application_once(monkeypatch):
    fake_runner = Mock()
    fake_runner.run_once.return_value = RunResult(
        total_jobs=2,
        processed=2,
        succeeded=2,
        failed=0,
        notified=1,
    )

    fake_build_application = Mock(return_value=fake_runner)

    monkeypatch.setattr(
        "src.main.build_application",
        fake_build_application,
    )

    from src.main import main

    result = main()

    fake_build_application.assert_called_once_with()
    fake_runner.run_once.assert_called_once_with()

    assert result.total_jobs == 2
    assert result.processed == 2
    assert result.succeeded == 2
    assert result.failed == 0
    assert result.notified == 1


def test_main_returns_run_result(monkeypatch):
    fake_runner = Mock()

    expected_result = RunResult(
        total_jobs=1,
        processed=1,
        succeeded=1,
        failed=0,
        notified=0,
    )

    fake_runner.run_once.return_value = expected_result

    monkeypatch.setattr(
        "src.main.build_application",
        Mock(return_value=fake_runner),
    )

    from src.main import main

    result = main()

    assert result is expected_result
