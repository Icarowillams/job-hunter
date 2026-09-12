from datetime import datetime

from src.application.orchestrator import ApplicationRunner
from src.domain.models import (
    CandidateProfile,
    Job,
    JobAnalysis,
    JobRequirement,
)
from src.infrastructure.database import Database
from src.infrastructure.job_analysis_repository import JobAnalysisRepository
from src.infrastructure.job_repository import JobRepository
from src.infrastructure.job_requirement_repository import JobRequirementRepository
from src.pipeline.analysis_pipeline import AnalysisPipeline


class FakeCollector:
    def __init__(self, jobs):
        self.jobs = jobs

    def fetch_jobs(self):
        return self.jobs


class FakeExtractor:
    def __init__(self, requirements):
        self.requirements = requirements

    def extract(self, job_id, description):
        return self.requirements


class FakeAnalyzer:
    def __init__(self, analysis):
        self.analysis = analysis
        self.calls = []

    def analyze(self, profile, job, requirements):
        self.calls.append(
            {
                "profile": profile,
                "job": job,
                "requirements": requirements,
            }
        )
        return self.analysis


class FakeNotifier:
    def __init__(self):
        self.calls = []

    def send_notification(self, analysis, job):
        self.calls.append(
            {
                "analysis": analysis,
                "job": job,
            }
        )


def build_database(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    return database


def build_profile():
    return CandidateProfile(
        id="profile-1",
        target_roles=["Software Engineer"],
        desired_seniority=["junior"],
        location="Recife",
        work_modes=["remote"],
        salary_expectation="3000",
        relocation_availability=False,
        availability_date=None,
        skills=["Python", "TypeScript"],
        explicit_gaps=[],
        experiences=[],
        educations=[],
        projects=[],
        languages=[],
        certifications=[],
        preferences={},
        restrictions=[],
        updated_at=datetime.now(),
    )


def build_job():
    return Job(
        id="job-1",
        title="Junior Software Engineer",
        company="Example Corp",
        location="Remote",
        work_mode="remote",
        description="Python and TypeScript developer",
        url="https://example.com/job-1",
        source="test",
        external_id="external-1",
        published_at=None,
        collected_at=datetime.now(),
    )


def build_requirement():
    return JobRequirement(
        id="req-1",
        job_id="job-1",
        name="Python",
        category="skill",
        mandatory=True,
        extraction_confidence=1.0,
    )


def build_analysis():
    return JobAnalysis(
        id="analysis-1",
        job_id="job-1",
        compatibility_score=90,
        priority_score=90,
        confidence_score=100,
        breakdown={},
        strengths=["Python"],
        gaps=[],
        unknown_requirements=[],
        hard_blocker=False,
        analyzed_at=datetime.now(),
    )


def test_application_runner_persists_complete_flow(tmp_path):
    database = build_database(tmp_path)

    job_repository = JobRepository(database)
    requirement_repository = JobRequirementRepository(database)
    analysis_repository = JobAnalysisRepository(database)

    job = build_job()
    requirement = build_requirement()
    analysis = build_analysis()
    profile = build_profile()

    collector = FakeCollector([job])
    extractor = FakeExtractor([requirement])
    analyzer = FakeAnalyzer(analysis)

    pipeline = AnalysisPipeline(
        analyzer=analyzer,
        analysis_repository=analysis_repository,
    )

    notifier = FakeNotifier()

    runner = ApplicationRunner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
        score_threshold=70,
    )

    result = runner.run_once()

    assert result.total_jobs == 1
    assert result.processed == 1
    assert result.succeeded == 1
    assert result.failed == 0
    assert result.notified == 1

    persisted_job = job_repository.get_by_id(job.id)

    assert persisted_job is not None
    assert persisted_job.title == job.title

    persisted_requirements = requirement_repository.get_by_job_id(job.id)

    assert len(persisted_requirements) == 1
    assert persisted_requirements[0].name == "Python"
    assert persisted_requirements[0].category == "skill"
    assert persisted_requirements[0].mandatory is True

    persisted_analysis = analysis_repository.get_by_id(analysis.id)

    assert persisted_analysis is not None
    assert persisted_analysis.compatibility_score == 90
    assert persisted_analysis.hard_blocker is False

    assert len(analyzer.calls) == 1
    assert analyzer.calls[0]["profile"] == profile
    assert analyzer.calls[0]["job"].id == job.id
    assert analyzer.calls[0]["requirements"] == [requirement]

    assert len(notifier.calls) == 1
    assert notifier.calls[0]["job"].id == job.id

def test_application_runner_is_idempotent_for_repeated_requirement_extraction(tmp_path):
    database = build_database(tmp_path)

    job_repository = JobRepository(database)
    requirement_repository = JobRequirementRepository(database)
    analysis_repository = JobAnalysisRepository(database)

    job = build_job()

    first_requirement = JobRequirement(
        id="req-1",
        job_id=job.id,
        name="Python",
        category="skill",
        mandatory=True,
        extraction_confidence=0.80,
    )

    second_requirement = JobRequirement(
        id="req-2",
        job_id=job.id,
        name="Python",
        category="skill",
        mandatory=True,
        extraction_confidence=0.95,
    )

    analysis = build_analysis()
    profile = build_profile()

    collector = FakeCollector([job])

    class RepeatedExtractor:
        def __init__(self):
            self.calls = 0

        def extract(self, job_id, description):
            self.calls += 1
            return [first_requirement] if self.calls == 1 else [second_requirement]

    extractor = RepeatedExtractor()

    analyzer = FakeAnalyzer(analysis)

    pipeline = AnalysisPipeline(
        analyzer=analyzer,
        analysis_repository=analysis_repository,
    )

    runner = ApplicationRunner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=None,
        score_threshold=70,
    )

    first_result = runner.run_once()
    second_result = runner.run_once()

    assert first_result.succeeded == 1
    assert second_result.succeeded == 1

    persisted_requirements = requirement_repository.get_by_job_id(job.id)

    assert len(persisted_requirements) == 1

    persisted = persisted_requirements[0]

    assert persisted.name == "Python"
    assert persisted.category == "skill"
    assert persisted.mandatory is True
    assert persisted.extraction_confidence == 0.95
