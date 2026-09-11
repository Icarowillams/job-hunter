from datetime import datetime, timezone

from src.domain.models import PipelineExecution
from src.infrastructure.database import Database
from src.infrastructure.pipeline_execution_repository import (
    PipelineExecutionRepository,
)


def test_save_and_get_execution(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    repository = PipelineExecutionRepository(database)

    execution = PipelineExecution(
        id="execution-1",
        execution_id="execution-1",
        schedule_id=None,
        started_at=datetime.now(timezone.utc),
        status="RUNNING",
        total_jobs=10,
        processed_jobs=0,
        failed_jobs=0,
    )

    repository.save(execution)

    result = repository.get_by_id("execution-1")

    assert result == execution


def test_save_execution_updates_existing_execution(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    repository = PipelineExecutionRepository(database)

    execution = PipelineExecution(
        id="execution-1",
        execution_id="execution-1",
        started_at=datetime.now(timezone.utc),
        status="RUNNING",
        total_jobs=10,
        processed_jobs=0,
        failed_jobs=0,
    )

    repository.save(execution)

    updated = execution.model_copy(
        update={
            "status": "COMPLETED",
            "processed_jobs": 10,
            "failed_jobs": 0,
            "ended_at": datetime.now(timezone.utc),
        }
    )

    repository.save(updated)

    result = repository.get_by_id("execution-1")

    assert result == updated


def test_get_by_id_returns_none_for_unknown_execution(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    repository = PipelineExecutionRepository(database)

    assert repository.get_by_id("missing") is None
