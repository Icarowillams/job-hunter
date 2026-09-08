from src.domain.models import CandidateProfile, Job, JobAnalysis, JobRequirement
from src.pipeline.analysis_pipeline import AnalysisPipeline


class FakeAnalyzer:
    def __init__(self, analysis: JobAnalysis):
        self.analysis = analysis

    def analyze(
        self,
        profile: CandidateProfile,
        job: Job,
        requirements: list[JobRequirement],
    ) -> JobAnalysis:
        return self.analysis


class FakeAnalysisRepository:
    def __init__(self):
        self.saved_analysis = None

    def save(self, analysis: JobAnalysis) -> None:
        self.saved_analysis = analysis


def test_pipeline_persists_analysis():
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

    expected_analysis = JobAnalysis(
        id="analysis-1",
        job_id=job.id,
        compatibility_score=100,
        priority_score=100,
        confidence_score=100,
        strengths=["Python"],
    )

    analyzer = FakeAnalyzer(expected_analysis)
    repository = FakeAnalysisRepository()

    pipeline = AnalysisPipeline(
        analyzer=analyzer,
        analysis_repository=repository,
    )

    result = pipeline.run(
        profile=profile,
        job=job,
        requirements=requirements,
    )

    assert result == expected_analysis
    assert repository.saved_analysis == expected_analysis
