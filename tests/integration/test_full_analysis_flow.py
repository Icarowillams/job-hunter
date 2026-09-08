from src.domain.models import CandidateProfile, Job, JobRequirement
from src.infrastructure.candidate_profile_repository import (
    CandidateProfileRepository,
)
from src.infrastructure.database import Database
from src.infrastructure.job_analysis_repository import JobAnalysisRepository
from src.infrastructure.job_repository import JobRepository
from src.infrastructure.job_requirement_repository import JobRequirementRepository
from src.pipeline.analysis_pipeline import AnalysisPipeline


def test_full_analysis_flow_persists_entities_and_analysis(tmp_path):
    database = Database(str(tmp_path / "job_hunter.db"))

    profile_repository = CandidateProfileRepository(database)
    job_repository = JobRepository(database)
    requirement_repository = JobRequirementRepository(database)
    analysis_repository = JobAnalysisRepository(database)

    profile = CandidateProfile(
        id="candidate-1",
        target_roles=["Backend Developer"],
        desired_seniority=["junior"],
        skills=["Python", "React"],
    )

    job = Job(
        id="job-1",
        source="test",
        title="Python Developer",
        company="Acme",
        description="Python developer with React experience.",
    )

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

    profile_repository.save(profile)
    job_repository.save(job)

    for requirement in requirements:
        requirement_repository.save(requirement)

    persisted_profile = profile_repository.get_by_id(profile.id)
    persisted_job = job_repository.get_by_id(job.id)
    persisted_requirements = requirement_repository.get_by_job_id(job.id)

    assert persisted_profile is not None
    assert persisted_job is not None
    assert len(persisted_requirements) == 2

    pipeline = AnalysisPipeline(
        analysis_repository=analysis_repository,
    )

    result = pipeline.run(
        profile=persisted_profile,
        job=persisted_job,
        requirements=persisted_requirements,
    )

    persisted_analysis = analysis_repository.get_by_id(result.id)

    assert persisted_analysis is not None
    assert persisted_analysis.job_id == job.id
    assert persisted_analysis.compatibility_score == 100
    assert persisted_analysis.confidence_score == 100
    assert persisted_analysis.hard_blocker is False
    assert "Python" in persisted_analysis.strengths
    assert "React" in persisted_analysis.strengths