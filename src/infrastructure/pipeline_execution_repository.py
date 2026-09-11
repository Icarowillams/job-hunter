from src.domain.models import PipelineExecution
from src.infrastructure.database import Database


class PipelineExecutionRepository:
    def __init__(self, database: Database):
        self.database = database

    def save(self, execution: PipelineExecution) -> None:
        with self.database.connect() as conn:
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
                ON CONFLICT(id) DO UPDATE SET
                    execution_id = excluded.execution_id,
                    schedule_id = excluded.schedule_id,
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    status = excluded.status,
                    total_jobs = excluded.total_jobs,
                    processed_jobs = excluded.processed_jobs,
                    failed_jobs = excluded.failed_jobs,
                    error_log = excluded.error_log
                """,
                (
                    execution.id,
                    execution.execution_id,
                    execution.schedule_id,
                    execution.started_at.isoformat(),
                    (
                        execution.ended_at.isoformat()
                        if execution.ended_at
                        else None
                    ),
                    execution.status,
                    execution.total_jobs,
                    execution.processed_jobs,
                    execution.failed_jobs,
                    execution.error_log,
                ),
            )

    def get_by_id(
        self,
        execution_id: str,
    ) -> PipelineExecution | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
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
                FROM pipeline_execution
                WHERE id = ?
                """,
                (execution_id,),
            ).fetchone()

        if row is None:
            return None

        return PipelineExecution(
            id=row[0],
            execution_id=row[1],
            schedule_id=row[2],
            started_at=row[3],
            ended_at=row[4],
            status=row[5],
            total_jobs=row[6],
            processed_jobs=row[7],
            failed_jobs=row[8],
            error_log=row[9],
        )
