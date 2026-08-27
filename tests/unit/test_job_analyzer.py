from src.domain.enums import MatchStatus
from src.domain.models import CandidateProfile, Job, JobRequirement
from src.analysis.job_analyzer import JobAnalyzer


def test_job_analyzer_creates_analysis_from_matches():
    profile = CandidateProfile(
        id="candidate-1",
        skills=["Python", "React"],
    )

    job = Job(
        id="job-1",
        source="test",
        title="Python Developer",
        company="Example",
        description="Python and React developer",
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

    analyzer = JobAnalyzer()

    analysis = analyzer.analyze(profile, job, requirements)

    assert analysis.job_id == "job-1"
    assert analysis.compatibility_score == 100
    assert analysis.hard_blocker is False
    assert analysis.confidence_score == 100


def test_job_analyzer_records_missing_requirements_as_gaps():
    profile = CandidateProfile(
        id="candidate-1",
        skills=["Python"],
    )

    job = Job(
        id="job-2",
        source="test",
        title="Backend Developer",
        company="Example",
        description="Python and Kubernetes developer",
    )

    requirements = [
        JobRequirement(
            id="req-1",
            job_id="job-2",
            name="Python",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
        JobRequirement(
            id="req-2",
            job_id="job-2",
            name="Kubernetes",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
    ]

    analyzer = JobAnalyzer()

    analysis = analyzer.analyze(profile, job, requirements)

    assert analysis.compatibility_score == 50
    assert analysis.hard_blocker is True
    assert "Kubernetes" in analysis.gaps