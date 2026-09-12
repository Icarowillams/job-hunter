from src.domain.models import JobRequirement
from src.infrastructure.database import Database


class JobRequirementRepository:
    def __init__(self, database: Database):
        self.database = database

    def save(self, requirement: JobRequirement) -> None:
        with self.database.connect() as conn:
            existing_by_id = conn.execute(
                """
                SELECT
                    id
                FROM job_requirement
                WHERE id = ?
                LIMIT 1
                """,
                (requirement.id,),
            ).fetchone()

            if existing_by_id is not None:
                conn.execute(
                    """
                    UPDATE job_requirement
                    SET
                        job_id = ?,
                        name = ?,
                        category = ?,
                        mandatory = ?,
                        extraction_confidence = ?
                    WHERE id = ?
                    """,
                    (
                        requirement.job_id,
                        requirement.name,
                        requirement.category,
                        int(requirement.mandatory),
                        requirement.extraction_confidence,
                        requirement.id,
                    ),
                )
                return

            existing_logical = conn.execute(
                """
                SELECT
                    id,
                    mandatory,
                    extraction_confidence
                FROM job_requirement
                WHERE job_id = ?
                  AND LOWER(name) = LOWER(?)
                  AND category = ?
                LIMIT 1
                """,
                (
                    requirement.job_id,
                    requirement.name,
                    requirement.category,
                ),
            ).fetchone()

            if existing_logical is None:
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
                return

            existing_id = existing_logical[0]
            existing_mandatory = bool(existing_logical[1])
            existing_confidence = existing_logical[2] or 0.0

            conn.execute(
                """
                UPDATE job_requirement
                SET
                    mandatory = ?,
                    extraction_confidence = ?
                WHERE id = ?
                """,
                (
                    int(existing_mandatory or requirement.mandatory),
                    max(
                        existing_confidence,
                        requirement.extraction_confidence,
                    ),
                    existing_id,
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