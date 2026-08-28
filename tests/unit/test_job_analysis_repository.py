import pytest

from src.domain.models import Job, JobAnalysis
from src.infrastructure.database import Database
from src.infrastructure.job_analysis_repository import JobAnalysisRepository


@pytest.fixture
def repository(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    return JobAnalysisRepository(database)


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


def test_save_and_get_analysis(repository, job):
    analysis = JobAnalysis(
        id="analysis-1",
        job_id=job.id,
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        breakdown={"skills": 85},
        strengths=["Python", "React"],
        gaps=["Docker"],
        unknown_requirements=[],
        hard_blocker=False,
        match_status="strong_match",
        classification="recommended",
        raw_output="Analysis output",
        scoring_version="1.0",
        extractor_version="1.0",
        normalizer_version="1.0",
        embedding_model_version="test-model",
    )

    repository.save(analysis)

    result = repository.get_by_id(analysis.id)

    assert result == analysis


def test_get_by_id_returns_none_when_analysis_does_not_exist(repository):
    result = repository.get_by_id("missing")

    assert result is None


def test_get_by_job_id_returns_analysis(repository, job):
    analysis = JobAnalysis(
        id="analysis-1",
        job_id=job.id,
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        breakdown={"skills": 85},
        strengths=["Python"],
        gaps=["Docker"],
        unknown_requirements=[],
        hard_blocker=False,
    )

    repository.save(analysis)

    result = repository.get_by_job_id(job.id)

    assert result == analysis


def test_save_analysis_updates_existing_analysis(repository, job):
    analysis = JobAnalysis(
        id="analysis-1",
        job_id=job.id,
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        breakdown={"skills": 85},
        strengths=["Python"],
        gaps=["Docker"],
        unknown_requirements=[],
        hard_blocker=False,
    )

    repository.save(analysis)

    updated = analysis.model_copy(
        update={
            "compatibility_score": 70,
            "priority_score": 75,
            "confidence_score": 80,
            "gaps": ["Docker", "PostgreSQL"],
            "hard_blocker": True,
        }
    )

    repository.save(updated)

    result = repository.get_by_id(analysis.id)

    assert result == updated