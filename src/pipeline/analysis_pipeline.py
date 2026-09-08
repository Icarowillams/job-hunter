from src.analysis.job_analyzer import JobAnalyzer
from src.domain.models import CandidateProfile, Job, JobAnalysis, JobRequirement


class AnalysisPipeline:
    def __init__(
        self,
        analyzer: JobAnalyzer | None = None,
        analysis_repository=None,
    ):
        self.analyzer = analyzer or JobAnalyzer()
        self.analysis_repository = analysis_repository

    def run(
        self,
        profile: CandidateProfile,
        job: Job,
        requirements: list[JobRequirement],
    ) -> JobAnalysis:
        analysis = self.analyzer.analyze(
            profile=profile,
            job=job,
            requirements=requirements,
        )

        if self.analysis_repository is not None:
            self.analysis_repository.save(analysis)

        return analysis