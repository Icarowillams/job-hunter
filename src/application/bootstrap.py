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
from src.infrastructure.job_analysis_repository import JobAnalysisRepository
from src.infrastructure.metric_repository import MetricRepository
from src.infrastructure.profile_loader import ProfileLoader
from src.ingestion.collectors.serpapi_job_collector import SerpApiJobCollector
from src.pipeline.analysis_pipeline import AnalysisPipeline


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

    analyzer = JobAnalyzer()
    analysis_repository = JobAnalysisRepository(database)
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
        job_repository=database,
        requirement_repository=database,
        extractor=extractor,
        notifier=notifier,
        score_threshold=score_threshold,
        metrics_service=metrics_service,
    )
