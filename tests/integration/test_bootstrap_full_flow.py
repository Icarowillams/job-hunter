from src.application.bootstrap import build_application
from src.domain.models import Job


class FakeCollector:
    def fetch_jobs(self):
        return [
            Job(
                id="job-integration-1",
                external_id="ext-1",
                source="test",
                title="Python Developer",
                company="Acme",
                description=(
                    "Python developer with experience in Python "
                    "and backend development."
                ),
                location="Remote",
                work_mode="remote",
                seniority="junior",
                url="https://example.com/job-1",
            )
        ]


def test_build_application_runs_full_flow_with_metrics(
    tmp_path,
):
    config_path = tmp_path / "config.yaml"
    profile_path = tmp_path / "profile.json"
    db_path = tmp_path / "job_hunter.db"

    config_path.write_text(
        """
paths:
  profile: "profile.json"
  db: "job_hunter.db"

notification:
  enabled: false
  minimum_score: 70

metrics:
  enabled: true
  persist: true

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
        """
{
  "id": "integration-profile",
  "target_roles": ["Python Developer"],
  "desired_seniority": ["Junior"],
  "location": "Remote",
  "work_modes": ["remote"],
  "skills": ["Python", "Backend"]
}
""",
        encoding="utf-8",
    )

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=db_path,
        collector=FakeCollector(),
    )

    result = runner.run_once()

    assert result.total_jobs == 1
    assert result.processed == 1
    assert result.succeeded == 1
    assert result.failed == 0

    with runner.job_repository.database.connect() as conn:
        executions = conn.execute(
            """
            SELECT id, execution_id, status
            FROM pipeline_execution
            """
        ).fetchall()

        metrics = conn.execute(
            """
            SELECT id, name, value, execution_id
            FROM metric
            """
        ).fetchall()

    assert executions
    assert metrics
    assert all(metric[3] == executions[0][0] for metric in metrics)
