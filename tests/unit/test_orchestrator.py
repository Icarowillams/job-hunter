from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from src.domain.enums import MatchStatus
from src.domain.models import (
    CandidateProfile,
    Job,
    JobAnalysis,
    JobRequirement,
)


@dataclass
class FakeJob:
    id: str
    source: str = "test"
    title: str = "Python Developer"
    company: str = "Acme"
    description: str = "Python developer"


class FakeCollector:
    def __init__(self, jobs=None, error=None):
        self.jobs = jobs or []
        self.error = error
        self.calls = 0

    def fetch_jobs(self):
        self.calls += 1

        if self.error:
            raise self.error

        return self.jobs


class FakeExtractor:
    def __init__(self, requirements_by_job=None, error=None):
        self.requirements_by_job = requirements_by_job or {}
        self.error = error
        self.calls = []

    def extract(self, job_id, description):
        self.calls.append((job_id, description))

        if self.error:
            raise self.error

        return self.requirements_by_job.get(job_id, [])


class FakePipeline:
    def __init__(self, analyses=None, error=None):
        self.analyses = analyses or {}
        self.error = error
        self.calls = []

    def run(self, profile, job, requirements):
        self.calls.append((profile, job, requirements))

        if self.error:
            raise self.error

        return self.analyses[job.id]


class FakeJobRepository:
    def __init__(self, error=None):
        self.saved_jobs = []
        self.error = error

    def save(self, job):
        if self.error:
            raise self.error

        self.saved_jobs.append(job)


class FakeRequirementRepository:
    def __init__(self, error=None):
        self.saved_requirements = []
        self.error = error

    def save(self, requirement):
        if self.error:
            raise self.error

        self.saved_requirements.append(requirement)


class FakeNotifier:
    def __init__(self, error=None):
        self.notifications = []
        self.error = error

    def send_notification(self, analysis, job):
        if self.error:
            raise self.error

        self.notifications.append((analysis, job))


@pytest.fixture
def profile():
    return CandidateProfile(
        id="candidate-1",
        skills=["Python", "React"],
    )


def make_job(
    job_id="job-1",
    title="Python Developer",
    description="Python developer",
):
    return Job(
        id=job_id,
        source="test",
        title=title,
        company="Acme",
        description=description,
    )


def make_requirements(job_id="job-1"):
    return [
        JobRequirement(
            id=f"{job_id}-req-1",
            job_id=job_id,
            name="Python",
            category="skill",
            mandatory=True,
        )
    ]


def make_analysis(
    job_id="job-1",
    score=100,
    hard_blocker=False,
):
    return JobAnalysis(
        id=f"analysis-{job_id}",
        job_id=job_id,
        compatibility_score=score,
        priority_score=score,
        confidence_score=100,
        strengths=["Python"],
        hard_blocker=hard_blocker,
    )


def build_runner(
    collector,
    profile,
    pipeline,
    job_repository,
    requirement_repository,
    extractor,
    notifier=None,
    score_threshold=70,
):
    from src.application.orchestrator import ApplicationRunner

    return ApplicationRunner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
        score_threshold=score_threshold,
    )


def test_run_once_processes_all_jobs(profile):
    job1 = make_job("job-1")
    job2 = make_job("job-2", title="React Developer")

    req1 = make_requirements("job-1")
    req2 = make_requirements("job-2")

    analysis1 = make_analysis("job-1")
    analysis2 = make_analysis("job-2")

    collector = FakeCollector([job1, job2])
    extractor = FakeExtractor(
        {
            "job-1": req1,
            "job-2": req2,
        }
    )
    pipeline = FakePipeline(
        {
            "job-1": analysis1,
            "job-2": analysis2,
        }
    )
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    result = runner.run_once()

    assert result.total_jobs == 2
    assert result.processed == 2
    assert result.succeeded == 2
    assert result.failed == 0
    assert result.notified == 0

    assert [job.id for job in job_repository.saved_jobs] == [
        "job-1",
        "job-2",
    ]


def test_run_once_extracts_and_persists_requirements(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(job.id)

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    runner.run_once()

    assert extractor.calls == [
        (job.id, job.description)
    ]

    assert requirement_repository.saved_requirements == requirements


def test_run_once_executes_pipeline(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(job.id)

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    result = runner.run_once()

    assert len(pipeline.calls) == 1

    called_profile, called_job, called_requirements = pipeline.calls[0]

    assert called_profile == profile
    assert called_job == job
    assert called_requirements == requirements

    assert result.results[0].compatibility_score == 100
    assert result.results[0].hard_blocker is False


def test_run_once_notifies_eligible_job(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(job.id, score=80)

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()
    notifier = FakeNotifier()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
    )

    result = runner.run_once()

    assert notifier.notifications == [(analysis, job)]
    assert result.notified == 1
    assert result.results[0].notified is True


def test_run_once_does_not_notify_low_score_job(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(job.id, score=69)

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()
    notifier = FakeNotifier()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
    )

    result = runner.run_once()

    assert notifier.notifications == []
    assert result.notified == 0
    assert result.results[0].notified is False


def test_run_once_does_not_notify_hard_blocker(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(
        job.id,
        score=100,
        hard_blocker=True,
    )

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()
    notifier = FakeNotifier()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
    )

    result = runner.run_once()

    assert notifier.notifications == []
    assert result.notified == 0
    assert result.results[0].notified is False


def test_run_once_works_without_notifier(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(job.id)

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=None,
    )

    result = runner.run_once()

    assert result.succeeded == 1
    assert result.failed == 0
    assert result.notified == 0
    assert result.results[0].notified is False


def test_one_job_failure_does_not_break_other_jobs(profile):
    job1 = make_job("job-1")
    job2 = make_job("job-2")

    req2 = make_requirements("job-2")
    analysis2 = make_analysis("job-2")

    class SelectiveExtractor(FakeExtractor):
        def extract(self, job_id, description):
            if job_id == "job-1":
                raise RuntimeError("extraction failed")

            return super().extract(job_id, description)

    collector = FakeCollector([job1, job2])
    extractor = SelectiveExtractor({"job-2": req2})
    pipeline = FakePipeline({"job-2": analysis2})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    result = runner.run_once()

    assert result.total_jobs == 2
    assert result.processed == 2
    assert result.succeeded == 1
    assert result.failed == 1

    assert result.results[0].success is False
    assert result.results[1].success is True


def test_repository_failure_marks_job_as_failed_and_continues(profile):
    job1 = make_job("job-1")
    job2 = make_job("job-2")

    requirements = make_requirements("job-2")
    analysis = make_analysis("job-2")

    class SelectiveRepository(FakeJobRepository):
        def save(self, job):
            if job.id == "job-1":
                raise RuntimeError("database failed")

            super().save(job)

    collector = FakeCollector([job1, job2])
    extractor = FakeExtractor({"job-2": requirements})
    pipeline = FakePipeline({"job-2": analysis})
    job_repository = SelectiveRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    result = runner.run_once()

    assert result.succeeded == 1
    assert result.failed == 1
    assert result.results[0].success is False
    assert "database failed" in result.results[0].error


def test_pipeline_failure_marks_job_as_failed_and_continues(profile):
    job1 = make_job("job-1")
    job2 = make_job("job-2")

    req1 = make_requirements("job-1")
    req2 = make_requirements("job-2")
    analysis2 = make_analysis("job-2")

    class SelectivePipeline(FakePipeline):
        def run(self, profile, job, requirements):
            if job.id == "job-1":
                raise RuntimeError("pipeline failed")

            return super().run(profile, job, requirements)

    collector = FakeCollector([job1, job2])
    extractor = FakeExtractor(
        {
            "job-1": req1,
            "job-2": req2,
        }
    )
    pipeline = SelectivePipeline({"job-2": analysis2})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    result = runner.run_once()

    assert result.succeeded == 1
    assert result.failed == 1
    assert result.results[0].success is False
    assert "pipeline failed" in result.results[0].error


def test_notifier_failure_does_not_fail_job(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(job.id)

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()
    notifier = FakeNotifier(
        error=RuntimeError("telegram unavailable")
    )

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
    )

    result = runner.run_once()

    assert result.succeeded == 1
    assert result.failed == 0
    assert result.notified == 0

    assert result.results[0].success is True
    assert result.results[0].notified is False
    assert result.results[0].notification_error == "telegram unavailable"


def test_collector_failure_raises(profile):
    collector = FakeCollector(
        error=RuntimeError("collector unavailable")
    )
    extractor = FakeExtractor()
    pipeline = FakePipeline()
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    with pytest.raises(RuntimeError, match="collector unavailable"):
        runner.run_once()


def test_run_result_contains_structured_job_results(profile):
    job = make_job()
    requirements = make_requirements(job.id)
    analysis = make_analysis(job.id, score=85)

    collector = FakeCollector([job])
    extractor = FakeExtractor({job.id: requirements})
    pipeline = FakePipeline({job.id: analysis})
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
    )

    result = runner.run_once()

    assert len(result.results) == 1

    item = result.results[0]

    assert item.job_id == job.id
    assert item.job_title == job.title
    assert item.success is True
    assert item.compatibility_score == 85
    assert item.hard_blocker is False
    assert item.notified is False
    assert item.error is None
    assert item.notification_error is None


def test_run_once_counts_multiple_outcomes_correctly(profile):
    job1 = make_job("job-1")
    job2 = make_job("job-2")
    job3 = make_job("job-3")

    req1 = make_requirements("job-1")
    req2 = make_requirements("job-2")
    req3 = make_requirements("job-3")

    analysis1 = make_analysis("job-1", score=90)
    analysis2 = make_analysis("job-2", score=60)
    analysis3 = make_analysis(
        "job-3",
        score=100,
        hard_blocker=True,
    )

    class SelectivePipeline(FakePipeline):
        def run(self, profile, job, requirements):
            if job.id == "job-2":
                raise RuntimeError("analysis failed")

            return super().run(profile, job, requirements)

    collector = FakeCollector([job1, job2, job3])
    extractor = FakeExtractor(
        {
            "job-1": req1,
            "job-2": req2,
            "job-3": req3,
        }
    )
    pipeline = SelectivePipeline(
        {
            "job-1": analysis1,
            "job-3": analysis3,
        }
    )
    job_repository = FakeJobRepository()
    requirement_repository = FakeRequirementRepository()
    notifier = FakeNotifier()

    runner = build_runner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
    )

    result = runner.run_once()

    assert result.total_jobs == 3
    assert result.processed == 3
    assert result.succeeded == 2
    assert result.failed == 1
    assert result.notified == 1

    assert result.results[0].notified is True
    assert result.results[1].success is False
    assert result.results[2].success is True
    assert result.results[2].notified is False
