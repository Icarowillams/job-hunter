import json

from src.domain.models import Job
from src.infrastructure.database import Database


class JobRepository:
    def __init__(self, database: Database):
        self.database = database

    def save(self, job: Job) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO job (
                    id,
                    external_id,
                    source,
                    title,
                    company,
                    description,
                    location,
                    work_mode,
                    seniority,
                    published_at,
                    discovered_at,
                    updated_at,
                    original_published_at,
                    url,
                    metadata,
                    normalized_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    external_id = excluded.external_id,
                    source = excluded.source,
                    title = excluded.title,
                    company = excluded.company,
                    description = excluded.description,
                    location = excluded.location,
                    work_mode = excluded.work_mode,
                    seniority = excluded.seniority,
                    published_at = excluded.published_at,
                    discovered_at = excluded.discovered_at,
                    updated_at = excluded.updated_at,
                    original_published_at = excluded.original_published_at,
                    url = excluded.url,
                    metadata = excluded.metadata,
                    normalized_hash = excluded.normalized_hash,
                    created_at = excluded.created_at
                """,
                (
                    job.id,
                    job.external_id,
                    job.source,
                    job.title,
                    job.company,
                    job.description,
                    job.location,
                    job.work_mode,
                    job.seniority,
                    job.published_at.isoformat() if job.published_at else None,
                    job.discovered_at.isoformat() if job.discovered_at else None,
                    job.updated_at.isoformat() if job.updated_at else None,
                    (
                        job.original_published_at.isoformat()
                        if job.original_published_at
                        else None
                    ),
                    job.url,
                    json.dumps(job.metadata),
                    job.normalized_hash,
                    job.created_at.isoformat() if job.created_at else None,
                ),
            )

    def get_by_id(self, job_id: str) -> Job | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    external_id,
                    source,
                    title,
                    company,
                    description,
                    location,
                    work_mode,
                    seniority,
                    published_at,
                    discovered_at,
                    updated_at,
                    original_published_at,
                    url,
                    metadata,
                    normalized_hash,
                    created_at
                FROM job
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        (
            id_,
            external_id,
            source,
            title,
            company,
            description,
            location,
            work_mode,
            seniority,
            published_at,
            discovered_at,
            updated_at,
            original_published_at,
            url,
            metadata,
            normalized_hash,
            created_at,
        ) = row

        return Job(
            id=id_,
            external_id=external_id,
            source=source,
            title=title,
            company=company,
            description=description,
            location=location,
            work_mode=work_mode,
            seniority=seniority,
            published_at=published_at,
            discovered_at=discovered_at,
            updated_at=updated_at,
            original_published_at=original_published_at,
            url=url,
            metadata=json.loads(metadata) if metadata else {},
            normalized_hash=normalized_hash,
            created_at=created_at,
        )