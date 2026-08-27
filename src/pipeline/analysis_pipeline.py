from src.analysis.job_analyzer import JobAnalyzer
from src.domain.models import CandidateProfile, Job, JobAnalysis, JobRequirement


class AnalysisPipeline:
    def __init__(self, analyzer: JobAnalyzer | None = None):
        self.analyzer = analyzer or JobAnalyzer()

    def run(
        self,
        profile: CandidateProfile,
        job: Job,
        requirements: list[JobRequirement],
    ) -> JobAnalysis:
        return self.analyzer.analyze(
            profile=profile,
            job=job,
            requirements=requirements,
        )