from datetime import datetime

from src.domain.metric import Metric


class MetricRepository:
    def __init__(self, database):
        self.database = database

    def save(self, metric: Metric) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO metric (
                    id,
                    name,
                    value,
                    created_at,
                    execution_id
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    metric.id,
                    metric.name,
                    metric.value,
                    metric.created_at.isoformat(),
                    metric.execution_id,
                ),
            )

    def list_by_execution(self, execution_id: str) -> list[Metric]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    name,
                    value,
                    created_at,
                    execution_id
                FROM metric
                WHERE execution_id = ?
                ORDER BY created_at ASC
                """,
                (execution_id,),
            ).fetchall()

        return [self._row_to_model(row) for row in rows]

    @staticmethod
    def _row_to_model(row) -> Metric:
        return Metric(
            id=row[0],
            name=row[1],
            value=row[2],
            created_at=datetime.fromisoformat(row[3]),
            execution_id=row[4],
        )
