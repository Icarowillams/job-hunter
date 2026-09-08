from pathlib import Path

import yaml

from src.analysis.job_analyzer import JobAnalyzer
from src.application.metrics.metrics_service import MetricsService
from src.application.orchestrator import ApplicationRunner
from src.extraction.requirement_extractor import RequirementExtractor
from src.infrastructure.candidate_profile_repository import CandidateProfileRepository
from src.infrastructure.database import Database
from src.infrastructure.metric_repository import MetricRepository
from src.infrastructure.profile_loader import ProfileLoader
from src.pipeline.analysis_pipeline import AnalysisPipeline


class NullJobCollector:
    def fetch_jobs(self):
        return []


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


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
    pipeline = AnalysisPipeline(
        analyzer=analyzer,
    )

    extractor = RequirementExtractor()

    if collector is None:
        collector = NullJobCollector()

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
