from datetime import datetime, timezone
from uuid import uuid4

from src.domain.metric import Metric


class MetricsService:
    def __init__(self, repository):
        self.repository = repository

    def record_run(self, execution_id: str, run_result) -> list[Metric]:
        metrics = [
            self._create_metric(
                name="jobs_total",
                value=run_result.total_jobs,
                execution_id=execution_id,
            ),
            self._create_metric(
                name="jobs_processed",
                value=run_result.processed,
                execution_id=execution_id,
            ),
            self._create_metric(
                name="jobs_succeeded",
                value=run_result.succeeded,
                execution_id=execution_id,
            ),
            self._create_metric(
                name="jobs_failed",
                value=run_result.failed,
                execution_id=execution_id,
            ),
            self._create_metric(
                name="notifications_sent",
                value=run_result.notified,
                execution_id=execution_id,
            ),
        ]

        for metric in metrics:
            self.repository.save(metric)

        return metrics

    @staticmethod
    def _create_metric(
        name: str,
        value: int,
        execution_id: str,
    ) -> Metric:
        return Metric(
            id=str(uuid4()),
            name=name,
            value=value,
            created_at=datetime.now(timezone.utc),
            execution_id=execution_id,
        )
