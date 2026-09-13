import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.analysis.job_analyzer import JobAnalyzer
from src.application.metrics.metrics_service import MetricsService
from src.application.orchestrator import ApplicationRunner
from src.extraction.requirement_extractor import RequirementExtractor
from src.infrastructure.candidate_profile_repository import CandidateProfileRepository
from src.infrastructure.database import Database
from src.infrastructure.email_notifier import EmailNotifier
from src.infrastructure.job_analysis_repository import JobAnalysisRepository
from src.infrastructure.job_repository import JobRepository
from src.infrastructure.job_requirement_repository import JobRequirementRepository
from src.infrastructure.metric_repository import MetricRepository
from src.infrastructure.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from src.infrastructure.profile_loader import ProfileLoader
from src.ingestion.collectors.fallback_job_collector import FallbackJobCollector
from src.ingestion.collectors.serpapi_google_search_collector import (
    SerpApiGoogleSearchCollector,
)
from src.ingestion.collectors.serpapi_job_collector import SerpApiJobCollector
from src.pipeline.analysis_pipeline import AnalysisPipeline
from src.infrastructure.smtp_client import SMTPClient
from src.infrastructure.notification_repository import NotificationRepository
from src.application.retry.retry_policy import RetryPolicy


class NullJobCollector:
    def fetch_jobs(self):
        return []


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    env_path = config_path.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _resolve_env_value(value):
    if not isinstance(value, str):
        return value

    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.getenv(env_name, "")

    return value


def _build_serpapi_collector(config: dict):
    serpapi_config = config.get("serpapi", {})
    query_params = serpapi_config.get("query_params", {})

    api_key = _resolve_env_value(
        serpapi_config.get("api_key", "")
    )
    query = query_params.get("query", "")
    location = query_params.get("location")
    limit = int(query_params.get("limit", 20))

    if not api_key:
        return NullJobCollector()

    return SerpApiJobCollector(
        api_key=api_key,
        query=query,
        location=location,
        limit=limit,
    )

def _build_email_notifier(
    config: dict,
    database: Database,
):
    email_config = config.get("email", {})
    retry_config = config.get("notification", {}).get("retry", {})

    smtp_server = _resolve_env_value(
        email_config.get("smtp_server", "")
    )
    smtp_port = int(
        email_config.get("smtp_port", 587)
    )
    username = _resolve_env_value(
        email_config.get("username", "")
    )
    password = _resolve_env_value(
        email_config.get("password", "")
    )
    sender = _resolve_env_value(
        email_config.get("from", username)
    )
    recipient = _resolve_env_value(
        email_config.get("to", username)
    )

    smtp_client = SMTPClient(
        host=smtp_server,
        port=smtp_port,
        username=username,
        password=password,
    )

    retry_policy = None

    if retry_config.get("enabled", False):
        retry_policy = RetryPolicy(
            max_attempts=int(
                retry_config.get("max_attempts", 3)
            ),
            delay_seconds=float(
                retry_config.get("delay_seconds", 2)
            ),
            backoff_multiplier=float(
                retry_config.get("backoff_multiplier", 2)
            ),
        )

    notification_repository = NotificationRepository(database)

    return EmailNotifier(
        smtp_client=smtp_client,
        sender=sender,
        recipient=recipient,
        retry_policy=retry_policy,
        notification_repository=notification_repository,
    )


def build_application(
    config_path: str | Path = "config.yaml",
    profile_path: str | Path | None = None,
    db_path: str | Path | None = None,
    collector=None,
    notifier=None,
) -> ApplicationRunner:
    config_path = Path(config_path)

    config = _load_config(config_path)

    paths_config = config.get("paths", {})
    notification_config = config.get("notification", {})
    metrics_config = config.get("metrics", {})

    resolved_profile_path = Path(
        profile_path
        if profile_path is not None
        else paths_config.get("profile", "data/profile.json")
    )

    resolved_db_path = Path(
        db_path
        if db_path is not None
        else paths_config.get("db", "data/job_hunter.db")
    )

    database = Database(db_path=str(resolved_db_path))

    profile_loader = ProfileLoader()
    profile = profile_loader.load(resolved_profile_path)

    profile_repository = CandidateProfileRepository(database)
    profile_repository.save(profile)

    job_repository = JobRepository(database)
    requirement_repository = JobRequirementRepository(database)
    analysis_repository = JobAnalysisRepository(database)
    execution_repository = PipelineExecutionRepository(database)

    analyzer = JobAnalyzer()

    pipeline = AnalysisPipeline(
        analyzer=analyzer,
        analysis_repository=analysis_repository,
    )

    extractor = RequirementExtractor()

    if collector is None:
        collector = _build_serpapi_collector(config)

    notification_enabled = notification_config.get("enabled", False)

    if not notification_enabled:
        notifier = None
    elif notifier is None:
        channel = notification_config.get("channel", "email")

        if channel == "email":
            notifier = _build_email_notifier(
                config=config,
                database=database,
            )
        else:
            notifier = None

    score_threshold = int(
        notification_config.get(
            "minimum_score",
            70,
        )
    )

    metrics_service = None

    if metrics_config.get("enabled", False):
        metric_repository = MetricRepository(database)
        metrics_service = MetricsService(metric_repository)

    return ApplicationRunner(
        collector=collector,
        profile=profile,
        pipeline=pipeline,
        job_repository=job_repository,
        requirement_repository=requirement_repository,
        extractor=extractor,
        notifier=notifier,
        score_threshold=score_threshold,
        metrics_service=metrics_service,
        execution_repository=execution_repository,
    )
