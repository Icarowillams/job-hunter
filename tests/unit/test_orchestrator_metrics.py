from types import SimpleNamespace

from src.application.orchestrator import ApplicationRunner


class FakeCollector:
    def fetch_jobs(self):
        return []


class FakeMetricService:
    def __init__(self):
        self.calls = []

    def record_run(self, execution_id, run_result):
        self.calls.append(
            {
                "execution_id": execution_id,
                "run_result": run_result,
            }
        )


def test_application_runner_records_metrics_for_run():
    metric_service = FakeMetricService()

    runner = ApplicationRunner(
        collector=FakeCollector(),
        profile=SimpleNamespace(),
        pipeline=SimpleNamespace(),
        job_repository=SimpleNamespace(),
        requirement_repository=SimpleNamespace(),
        extractor=SimpleNamespace(),
        notifier=None,
        score_threshold=70,
        metrics_service=metric_service,
    )

    result = runner.run_once()

    assert len(metric_service.calls) == 1

    call = metric_service.calls[0]

    assert call["execution_id"]
    assert call["run_result"] is result


def test_application_runner_generates_different_execution_ids():
    metric_service = FakeMetricService()

    runner = ApplicationRunner(
        collector=FakeCollector(),
        profile=SimpleNamespace(),
        pipeline=SimpleNamespace(),
        job_repository=SimpleNamespace(),
        requirement_repository=SimpleNamespace(),
        extractor=SimpleNamespace(),
        notifier=None,
        score_threshold=70,
        metrics_service=metric_service,
    )

    runner.run_once()
    runner.run_once()

    assert len(metric_service.calls) == 2

    first_id = metric_service.calls[0]["execution_id"]
    second_id = metric_service.calls[1]["execution_id"]

    assert first_id
    assert second_id
    assert first_id != second_id
