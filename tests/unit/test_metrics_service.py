from types import SimpleNamespace

from src.application.metrics.metrics_service import MetricsService


class FakeMetricRepository:
    def __init__(self):
        self.saved = []

    def save(self, metric):
        self.saved.append(metric)


def test_metrics_service_records_run_metrics():
    repository = FakeMetricRepository()
    service = MetricsService(repository)

    run_result = SimpleNamespace(
        total_jobs=10,
        processed=8,
        succeeded=7,
        failed=1,
        notified=3,
    )

    metrics = service.record_run(
        execution_id="execution-1",
        run_result=run_result,
    )

    assert len(metrics) == 5
    assert len(repository.saved) == 5

    values = {
        metric.name: metric.value
        for metric in repository.saved
    }

    assert values == {
        "jobs_total": 10,
        "jobs_processed": 8,
        "jobs_succeeded": 7,
        "jobs_failed": 1,
        "notifications_sent": 3,
    }

    assert all(
        metric.execution_id == "execution-1"
        for metric in repository.saved
    )


def test_metrics_service_returns_persisted_metrics():
    repository = FakeMetricRepository()
    service = MetricsService(repository)

    run_result = SimpleNamespace(
        total_jobs=2,
        processed=2,
        succeeded=2,
        failed=0,
        notified=1,
    )

    metrics = service.record_run(
        execution_id="execution-42",
        run_result=run_result,
    )

    assert metrics == repository.saved
    assert all(metric.id for metric in metrics)
    assert all(metric.created_at is not None for metric in metrics)


def test_metrics_service_records_zero_values():
    repository = FakeMetricRepository()
    service = MetricsService(repository)

    run_result = SimpleNamespace(
        total_jobs=0,
        processed=0,
        succeeded=0,
        failed=0,
        notified=0,
    )

    metrics = service.record_run(
        execution_id="execution-empty",
        run_result=run_result,
    )

    values = {
        metric.name: metric.value
        for metric in metrics
    }

    assert values == {
        "jobs_total": 0,
        "jobs_processed": 0,
        "jobs_succeeded": 0,
        "jobs_failed": 0,
        "notifications_sent": 0,
    }
