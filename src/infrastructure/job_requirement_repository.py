from src.domain.models import JobRequirement
from src.infrastructure.database import Database


class JobRequirementRepository:
    def __init__(self, database: Database):
        self.database = database

    def save(self, requirement: JobRequirement) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO job_requirement (
                    id,
                    job_id,
                    name,
                    category,
                    mandatory,
                    extraction_confidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    job_id = excluded.job_id,
                    name = excluded.name,
                    category = excluded.category,
                    mandatory = excluded.mandatory,
                    extraction_confidence = excluded.extraction_confidence
                """,
                (
                    requirement.id,
                    requirement.job_id,
                    requirement.name,
                    requirement.category,
                    int(requirement.mandatory),
                    requirement.extraction_confidence,
                ),
            )

    def get_by_id(self, requirement_id: str) -> JobRequirement | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    job_id,
                    name,
                    category,
                    mandatory,
                    extraction_confidence
                FROM job_requirement
                WHERE id = ?
                """,
                (requirement_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    def get_by_job_id(self, job_id: str) -> list[JobRequirement]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    job_id,
                    name,
                    category,
                    mandatory,
                    extraction_confidence
                FROM job_requirement
                WHERE job_id = ?
                ORDER BY id
                """,
                (job_id,),
            ).fetchall()

        return [self._row_to_model(row) for row in rows]

    @staticmethod
    def _row_to_model(row) -> JobRequirement:
        return JobRequirement(
            id=row[0],
            job_id=row[1],
            name=row[2],
            category=row[3],
            mandatory=bool(row[4]),
            extraction_confidence=row[5],
        )