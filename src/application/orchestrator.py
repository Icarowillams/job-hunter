from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from src.domain.models import CandidateProfile, Job, JobAnalysis, PipelineExecution


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
        execution_repository=None,
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
        self.execution_repository = execution_repository

    def run_once(self) -> RunResult:
        execution_id = str(uuid4())
        started_at = datetime.now(timezone.utc)

        self._save_execution(
            PipelineExecution(
                id=execution_id,
                execution_id=execution_id,
                schedule_id=None,
                started_at=started_at,
                ended_at=None,
                status="RUNNING",
                total_jobs=0,
                processed_jobs=0,
                failed_jobs=0,
                error_log=None,
            )
        )

        results: list[JobProcessingResult] = []
        errors: list[str] = []
        notified = 0

        try:
            jobs = self.collector.fetch_jobs()

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

            succeeded = sum(
                1
                for result in results
                if result.success
            )

            failed = sum(
                1
                for result in results
                if not result.success
            )

            for result in results:
                if result.error:
                    errors.append(
                        f"{result.job_id}: {result.error}"
                    )

            run_result = RunResult(
                total_jobs=len(jobs),
                processed=len(results),
                succeeded=succeeded,
                failed=failed,
                notified=notified,
                results=results,
                errors=errors,
            )

            self._save_execution(
                PipelineExecution(
                    id=execution_id,
                    execution_id=execution_id,
                    schedule_id=None,
                    started_at=started_at,
                    ended_at=datetime.now(timezone.utc),
                    status="COMPLETED",
                    total_jobs=run_result.total_jobs,
                    processed_jobs=run_result.processed,
                    failed_jobs=run_result.failed,
                    error_log=(
                        "\n".join(run_result.errors)
                        if run_result.errors
                        else None
                    ),
                )
            )

            if self.metrics_service is not None:
                self.metrics_service.record_run(
                    execution_id=execution_id,
                    run_result=run_result,
                )

            return run_result

        except Exception as exc:
            error_message = str(exc)

            self._save_execution(
                PipelineExecution(
                    id=execution_id,
                    execution_id=execution_id,
                    schedule_id=None,
                    started_at=started_at,
                    ended_at=datetime.now(timezone.utc),
                    status="FAILED",
                    total_jobs=len(results),
                    processed_jobs=len(results),
                    failed_jobs=sum(
                        1
                        for result in results
                        if not result.success
                    ),
                    error_log=error_message,
                )
            )

            raise

    def _save_execution(
        self,
        execution: PipelineExecution,
    ) -> None:
        if self.execution_repository is not None:
            self.execution_repository.save(execution)

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
