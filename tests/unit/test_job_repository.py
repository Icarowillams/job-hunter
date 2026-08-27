import pytest

from src.domain.models import Job
from src.infrastructure.database import Database
from src.infrastructure.job_repository import JobRepository


@pytest.fixture
def repository(tmp_path):
    database = Database(str(tmp_path / "job_hunter.db"))
    return JobRepository(database)


def make_job(**overrides):
    data = {
        "id": "job-1",
        "external_id": "ext-1",
        "source": "test",
        "title": "Python Developer",
        "company": "Acme",
        "description": "Python developer with React experience.",
        "location": "Remote",
        "work_mode": "remote",
        "seniority": "junior",
        "url": "https://example.com/job-1",
        "metadata": {"source_id": "123"},
    }
    data.update(overrides)
    return Job(**data)


def test_save_and_get_job(repository):
    job = make_job()

    repository.save(job)

    result = repository.get_by_id(job.id)

    assert result == job


def test_get_by_id_returns_none_when_job_does_not_exist(repository):
    result = repository.get_by_id("missing")

    assert result is None


def test_save_job_updates_existing_job(repository):
    job = make_job()

    repository.save(job)

    updated_job = job.model_copy(
        update={
            "title": "Senior Python Developer",
            "company": "New Acme",
        }
    )

    repository.save(updated_job)

    result = repository.get_by_id(job.id)

    assert result == updated_job

def test_save_and_get_job_preserves_dates_and_metadata(repository):
    from datetime import datetime, timezone

    published_at = datetime(2026, 8, 27, 15, 30, tzinfo=timezone.utc)
    discovered_at = datetime(2026, 8, 27, 16, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 8, 27, 16, 5, tzinfo=timezone.utc)

    job = make_job(
        published_at=published_at,
        discovered_at=discovered_at,
        created_at=created_at,
        metadata={
            "source_id": "123",
            "remote": True,
            "tags": ["python", "backend"],
        },
    )

    repository.save(job)

    result = repository.get_by_id(job.id)

    assert result == job
    assert result.published_at == published_at
    assert result.discovered_at == discovered_at
    assert result.created_at == created_at
    assert result.metadata == job.metadata