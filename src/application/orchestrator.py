from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from src.domain.models import CandidateProfile, Job, JobAnalysis


@dataclass
class JobProcessingResult:
    job_id: str
    job_title: str
    success: bool
    compatibility_score: Optional[int] = None
    hard_blocker: Optional[bool] = None
    notified: bool = False
    error: Optional[str] = None
    notification_error: Optional[str] = None


@dataclass
class RunResult:
    total_jobs: int
    processed: int
    succeeded: int
    failed: int
    notified: int
    results: list[JobProcessingResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ApplicationRunner:
    def __init__(
        self,
        collector,
        profile: CandidateProfile,
        pipeline,
        job_repository,
        requirement_repository,
        extractor,
        notifier=None,
        score_threshold: int = 70,
        metrics_service=None,
    ):
        self.collector = collector
        self.profile = profile
        self.pipeline = pipeline
        self.job_repository = job_repository
        self.requirement_repository = requirement_repository
        self.extractor = extractor
        self.notifier = notifier
        self.score_threshold = score_threshold
        self.metrics_service = metrics_service

    def run_once(self) -> RunResult:
        jobs = self.collector.fetch_jobs()

        results: list[JobProcessingResult] = []
        errors: list[str] = []
        notified = 0

        for job in jobs:
            result = self._process_job(job)

            results.append(result)

            if result.notification_error:
                errors.append(
                    f"{job.id}: notification failed: "
                    f"{result.notification_error}"
                )

            if result.notified:
                notified += 1

        succeeded = sum(1 for result in results if result.success)
        failed = sum(1 for result in results if not result.success)

        for result in results:
            if result.error:
                errors.append(f"{result.job_id}: {result.error}")

        run_result = RunResult(
            total_jobs=len(jobs),
            processed=len(results),
            succeeded=succeeded,
            failed=failed,
            notified=notified,
            results=results,
            errors=errors,
        )

        if self.metrics_service is not None:
            self.metrics_service.record_run(
                execution_id=str(uuid4()),
                run_result=run_result,
            )

        return run_result

    def _process_job(self, job: Job) -> JobProcessingResult:
        result = JobProcessingResult(
            job_id=job.id,
            job_title=job.title,
            success=False,
        )

        try:
            self.job_repository.save(job)

            requirements = self.extractor.extract(
                job.id,
                job.description,
            )

            for requirement in requirements:
                self.requirement_repository.save(requirement)

            analysis: JobAnalysis = self.pipeline.run(
                profile=self.profile,
                job=job,
                requirements=requirements,
            )

            result.compatibility_score = analysis.compatibility_score
            result.hard_blocker = analysis.hard_blocker
            result.success = True

            if (
                self.notifier is not None
                and analysis.compatibility_score >= self.score_threshold
                and not analysis.hard_blocker
            ):
                try:
                    self.notifier.send_notification(
                        analysis,
                        job,
                    )
                    result.notified = True
                except Exception as exc:
                    result.notification_error = str(exc)

        except Exception as exc:
            result.error = str(exc)

        return result
