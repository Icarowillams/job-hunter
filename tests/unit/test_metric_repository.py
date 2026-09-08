from datetime import datetime, timezone

from src.domain.metric import Metric
from src.infrastructure.database import Database
from src.infrastructure.metric_repository import MetricRepository


def _create_execution(database, execution_id="execution-1"):
    with database.connect() as conn:
        conn.execute(
            """
            INSERT INTO pipeline_execution (
                id,
                execution_id,
                schedule_id,
                started_at,
                ended_at,
                status,
                total_jobs,
                processed_jobs,
                failed_jobs,
                error_log
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                execution_id,
                None,
                datetime.now(timezone.utc).isoformat(),
                None,
                "RUNNING",
                0,
                0,
                0,
                None,
            ),
        )


def test_metric_repository_saves_and_reads_metric(tmp_path):
    database = Database(db_path=str(tmp_path / "test.db"))
    repository = MetricRepository(database)

    _create_execution(database)

    metric = Metric(
        id="metric-1",
        name="jobs_processed",
        value=10,
        created_at=datetime.now(timezone.utc),
        execution_id="execution-1",
    )

    repository.save(metric)

    metrics = repository.list_by_execution("execution-1")

    assert len(metrics) == 1
    assert metrics[0].id == "metric-1"
    assert metrics[0].name == "jobs_processed"
    assert metrics[0].value == 10
    assert metrics[0].execution_id == "execution-1"


def test_metric_repository_returns_empty_list_for_unknown_execution(tmp_path):
    database = Database(db_path=str(tmp_path / "test.db"))
    repository = MetricRepository(database)

    assert repository.list_by_execution("unknown") == []


def test_metric_repository_keeps_metrics_ordered_by_creation_time(tmp_path):
    database = Database(db_path=str(tmp_path / "test.db"))
    repository = MetricRepository(database)

    _create_execution(database)

    first = Metric(
        id="metric-1",
        name="jobs_processed",
        value=5,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        execution_id="execution-1",
    )

    second = Metric(
        id="metric-2",
        name="jobs_failed",
        value=2,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        execution_id="execution-1",
    )

    repository.save(second)
    repository.save(first)

    metrics = repository.list_by_execution("execution-1")

    assert [metric.id for metric in metrics] == [
        "metric-1",
        "metric-2",
    ]
