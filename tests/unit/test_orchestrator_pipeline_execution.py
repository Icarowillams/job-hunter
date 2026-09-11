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


class FakeExecutionRepository:
    def __init__(self):
        self.saved = []

    def save(self, execution):
        self.saved.append(execution)


def test_application_runner_persists_pipeline_execution(
    tmp_path,
):
    metric_service = FakeMetricService()
    execution_repository = FakeExecutionRepository()

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
        execution_repository=execution_repository,
    )

    result = runner.run_once()

    assert len(execution_repository.saved) == 2

    running_execution = execution_repository.saved[0]
    execution = execution_repository.saved[1]

    assert running_execution.id
    assert running_execution.status == "RUNNING"
    assert execution.id
    assert execution.execution_id == execution.id
    assert running_execution.id == execution.id
    assert running_execution.execution_id == execution.execution_id
    assert execution.status == "COMPLETED"
    assert execution.total_jobs == result.total_jobs
    assert execution.processed_jobs == result.processed
    assert execution.failed_jobs == result.failed

    assert len(metric_service.calls) == 1
    assert metric_service.calls[0]["execution_id"] == execution.id
