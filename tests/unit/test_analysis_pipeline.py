from src.domain.enums import MatchStatus
from src.domain.models import CandidateProfile, Job, JobRequirement
from src.pipeline.analysis_pipeline import AnalysisPipeline


def test_pipeline_produces_job_analysis():
    profile = CandidateProfile(
        id="candidate-1",
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
            job_id="job-1",
            name="Python",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
        JobRequirement(
            id="req-2",
            job_id="job-1",
            name="React",
            category="skill",
            mandatory=False,
            extraction_confidence=0.90,
        ),
    ]

    pipeline = AnalysisPipeline()

    result = pipeline.run(profile, job, requirements)

    assert result.job_id == job.id
    assert result.compatibility_score == 100
    assert result.hard_blocker is False
    assert "Python" in result.strengths
    assert "React" in result.strengths


def test_pipeline_preserves_missing_requirements_as_gaps():
    profile = CandidateProfile(
        id="candidate-1",
        skills=["Python"],
    )

    job = Job(
        id="job-1",
        source="test",
        title="Backend Developer",
        company="Acme",
        description="Python and Kubernetes developer.",
    )

    requirements = [
        JobRequirement(
            id="req-1",
            job_id="job-1",
            name="Python",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
        JobRequirement(
            id="req-2",
            job_id="job-1",
            name="Kubernetes",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
    ]

    pipeline = AnalysisPipeline()

    result = pipeline.run(profile, job, requirements)

    assert result.job_id == job.id
    assert result.hard_blocker is True
    assert "Kubernetes" in result.gaps