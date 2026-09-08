from src.domain.models import CandidateProfile, Job, JobRequirement
from src.infrastructure.database import Database
from src.infrastructure.job_analysis_repository import JobAnalysisRepository
from src.pipeline.analysis_pipeline import AnalysisPipeline


def test_pipeline_persists_analysis_in_database(tmp_path):
    database = Database(str(tmp_path / "job_hunter.db"))
    repository = JobAnalysisRepository(database)

    profile = CandidateProfile(
        id="candidate-1",
        skills=["Python"],
    )

    job = Job(
        id="job-1",
        source="test",
        title="Python Developer",
        company="Acme",
        description="Python developer",
    )

    requirements = [
        JobRequirement(
            id="req-1",
            job_id=job.id,
            name="Python",
            category="skill",
            mandatory=True,
        )
    ]

    # O repository possui FK para job, então o job precisa existir.
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
                job.id,
                job.source,
                job.title,
                job.company,
                job.description,
            ),
        )

    pipeline = AnalysisPipeline(
        analysis_repository=repository,
    )

    result = pipeline.run(
        profile=profile,
        job=job,
        requirements=requirements,
    )

    persisted = repository.get_by_id(result.id)

    assert persisted is not None
    assert persisted.id == result.id
    assert persisted.job_id == job.id
    assert persisted.compatibility_score == 100
    assert persisted.confidence_score == 100
    assert persisted.strengths == ["Python"]
    assert persisted.hard_blocker is False