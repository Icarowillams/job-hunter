from src.infrastructure.email_notifier import EmailNotifier
from src.application.bootstrap import build_application
from src.application.orchestrator import ApplicationRunner
from src.ingestion.collectors.serpapi_job_collector import SerpApiJobCollector

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

def test_build_application_creates_serpapi_collector_from_environment(
    tmp_path,
    monkeypatch,
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
  api_key: "${SERPAPI_API_KEY}"
  query_params:
    location: "Recife, PE"
    query: "estágio python"
    limit: 15
""",
        encoding="utf-8",
    )

    profile_path.write_text(
        '{"id": "test-profile", "skills": ["Python"]}',
        encoding="utf-8",
    )

    monkeypatch.setenv("SERPAPI_API_KEY", "test-serpapi-key")

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
    )

    assert isinstance(runner.collector, SerpApiJobCollector)

    primary = runner.collector

    assert isinstance(primary, SerpApiJobCollector)
    assert primary.api_key == "test-serpapi-key"
    assert primary.query == "estágio python"
    assert primary.location == "Recife, PE"
    assert primary.limit == 15


def test_build_application_accepts_injected_collector(
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
    query: "estágio"
    limit: 20
""",
        encoding="utf-8",
    )

    profile_path.write_text(
        '{"id": "test-profile"}',
        encoding="utf-8",
    )

    fake_collector = object()

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
        collector=fake_collector,
    )

    assert runner.collector is fake_collector


def test_build_application_loads_serpapi_key_from_dotenv(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "config.yaml"
    profile_path = tmp_path / "profile.json"
    env_path = tmp_path / ".env"

    config_path.write_text(
        """
paths:
  profile: "profile.json"
  db: "job_hunter.db"

notification:
  enabled: false

serpapi:
  api_key: "${SERPAPI_API_KEY}"
  query_params:
    location: "Recife, PE"
    query: "estágio python"
    limit: 10
""",
        encoding="utf-8",
    )

    profile_path.write_text(
        '{"id": "test-profile", "skills": ["Python"]}',
        encoding="utf-8",
    )

    env_path.write_text(
        "SERPAPI_API_KEY=dotenv-test-key\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
    )

    assert isinstance(runner.collector, SerpApiJobCollector)
    assert runner.collector.api_key == "dotenv-test-key"


def test_build_application_injects_job_analysis_repository(
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

    assert runner.pipeline.analysis_repository is not None
    assert runner.pipeline.analysis_repository.database is runner.job_repository.database




def test_build_application_creates_email_notifier_from_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"

    config_path.write_text(
        """
notification:
  enabled: true
  channel: email
  minimum_score: 70
  retry:
    enabled: true
    max_attempts: 3
    delay_seconds: 0
    backoff_multiplier: 1

email:
  smtp_server: smtp.example.com
  smtp_port: 587
  username: ${EMAIL_USERNAME}
  password: ${EMAIL_PASSWORD}
  from: hunter@example.com
  to: user@example.com

paths:
  profile: data/profile.json
  db: data/job_hunter.db

metrics:
  enabled: false
""",
        encoding="utf-8",
    )

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        '{"id": "test-profile"}',
        encoding="utf-8",
    )

    monkeypatch.setenv("EMAIL_USERNAME", "hunter@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "test-password")

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "test.db",
        collector=object(),
    )

    assert isinstance(runner.notifier, EmailNotifier)
    assert runner.notifier.sender == "hunter@example.com"
    assert runner.notifier.recipient == "user@example.com"
