import pytest

from src.domain.models import Job, JobRequirement
from src.infrastructure.database import Database
from src.infrastructure.job_requirement_repository import JobRequirementRepository


@pytest.fixture
def repository(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    return JobRequirementRepository(database)


@pytest.fixture
def job(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    with database.connect() as conn:
        conn.execute(
            """
            INSERT INTO job (
                id,
                source,
                title,
                company,
                description
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "job-1",
                "test",
                "Python Developer",
                "Acme",
                "Python developer position.",
            ),
        )

    return Job(
        id="job-1",
        source="test",
        title="Python Developer",
        company="Acme",
        description="Python developer position.",
    )


def test_save_and_get_requirement(repository, job):
    requirement = JobRequirement(
        id="req-1",
        job_id=job.id,
        name="Python",
        category="skill",
        mandatory=True,
        extraction_confidence=0.95,
    )

    repository.save(requirement)

    result = repository.get_by_id(requirement.id)

    assert result == requirement


def test_get_by_id_returns_none_when_requirement_does_not_exist(repository):
    result = repository.get_by_id("missing")

    assert result is None


def test_get_by_job_id_returns_requirements(repository, job):
    requirements = [
        JobRequirement(
            id="req-1",
            job_id=job.id,
            name="Python",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
        JobRequirement(
            id="req-2",
            job_id=job.id,
            name="React",
            category="skill",
            mandatory=False,
            extraction_confidence=0.90,
        ),
    ]

    for requirement in requirements:
        repository.save(requirement)

    result = repository.get_by_job_id(job.id)

    assert result == requirements


def test_save_requirement_updates_existing_requirement(repository, job):
    requirement = JobRequirement(
        id="req-1",
        job_id=job.id,
        name="Python",
        category="skill",
        mandatory=True,
        extraction_confidence=0.80,
    )

    repository.save(requirement)

    updated = requirement.model_copy(
        update={
            "name": "Python 3",
            "extraction_confidence": 0.95,
        }
    )

    repository.save(updated)

    result = repository.get_by_id(requirement.id)

    assert result == updated


def test_deleting_job_cascades_to_requirements(repository, job):
    requirement = JobRequirement(
        id="req-1",
        job_id=job.id,
        name="Python",
        category="skill",
        mandatory=True,
        extraction_confidence=0.95,
    )

    repository.save(requirement)

    with repository.database.connect() as conn:
        conn.execute("DELETE FROM job WHERE id = ?", (job.id,))

    assert repository.get_by_id(requirement.id) is None