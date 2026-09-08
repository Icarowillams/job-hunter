from pathlib import Path

import pytest

from src.application.bootstrap import build_application
from src.application.orchestrator import ApplicationRunner


def test_build_application_returns_application_runner(tmp_path):
    config_path = tmp_path / "config.yaml"
    profile_path = tmp_path / "profile.json"

    config_path.write_text(
        """
paths:
  profile: "profile.json"
  db: "job_hunter.db"

notification:
  enabled: false
  minimum_score: 70

serpapi:
  api_key: ""
  query_params:
    location: "Recife, PE"
    query: "estágio desenvolvimento"
    limit: 20
""",
        encoding="utf-8",
    )

    profile_path.write_text(
        """
{
  "id": "test-profile",
  "target_roles": ["Backend Developer"],
  "desired_seniority": ["Junior"],
  "location": "Recife, PE",
  "work_modes": ["remote"],
  "skills": ["Python", "TypeScript"]
}
""",
        encoding="utf-8",
    )

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
    )

    assert isinstance(runner, ApplicationRunner)

    assert runner.profile.id == "test-profile"

    assert runner.job_repository is not None
    assert runner.requirement_repository is not None

    assert runner.pipeline is not None
    assert runner.extractor is not None

    assert runner.notifier is None
    assert runner.score_threshold == 70


def test_build_application_creates_database(tmp_path):
    config_path = tmp_path / "config.yaml"
    profile_path = tmp_path / "profile.json"
    db_path = tmp_path / "nested" / "job_hunter.db"

    config_path.write_text(
        """
paths:
  profile: "profile.json"
  db: "job_hunter.db"

notification:
  enabled: false

serpapi:
  api_key: ""
  query_params:
    location: "Recife, PE"
    query: "estágio"
    limit: 20
""",
        encoding="utf-8",
    )

    profile_path.write_text(
        '{"id": "test-profile", "skills": ["Python"]}',
        encoding="utf-8",
    )

    build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=db_path,
    )

    assert db_path.exists()


def test_build_application_uses_configured_notification_threshold(tmp_path):
    config_path = tmp_path / "config.yaml"
    profile_path = tmp_path / "profile.json"

    config_path.write_text(
        """
paths:
  profile: "profile.json"
  db: "job_hunter.db"

notification:
  enabled: false
  minimum_score: 85

serpapi:
  api_key: ""
  query_params:
    location: "Recife, PE"
    query: "estágio"
    limit: 20
""",
        encoding="utf-8",
    )

    profile_path.write_text(
        '{"id": "test-profile"}',
        encoding="utf-8",
    )

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
    )

    assert runner.score_threshold == 85
