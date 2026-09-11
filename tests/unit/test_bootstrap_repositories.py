from pathlib import Path

from src.application.bootstrap import build_application
from src.infrastructure.job_repository import JobRepository
from src.infrastructure.job_requirement_repository import JobRequirementRepository


def test_build_application_injects_job_repositories(
    tmp_path,
):
    config_path = tmp_path / "config.yaml"
    profile_path = tmp_path / "profile.json"

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
    query: "estagio python"
    limit: 20
""",
        encoding="utf-8",
    )

    profile_path.write_text(
        '{"id": "test-profile", "skills": ["Python"]}',
        encoding="utf-8",
    )

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
    )

    assert isinstance(
        runner.job_repository,
        JobRepository,
    )

    assert isinstance(
        runner.requirement_repository,
        JobRequirementRepository,
    )
