import json

from src.analysis.job_analyzer import JobAnalyzer
from src.application.bootstrap import build_application
from src.domain.models import Job
from src.extraction.requirement_extractor import RequirementExtractor
from src.infrastructure.knowledge_repository import KnowledgeRepository


CONFIG = """
paths:
  profile: "profile.json"
  db: "job_hunter.db"

notification:
  enabled: false
  minimum_score: 70

metrics:
  enabled: false

serpapi:
  api_key: ""
  query_params:
    location: "Recife, PE"
    query: "estagio python"
    limit: 20
"""


PROFILE_V1 = {
    "id": "kb-integration-profile",
    "target_roles": ["Python Developer"],
    "desired_seniority": ["Junior"],
    "location": "Remote",
    "work_modes": ["remote"],
    "skills": ["Python", "Backend"],
    "experiences": [
        {
            "company": "Acme",
            "role": "Developer",
            "period": "2024-2025",
            "responsibilities": "Built APIs.",
        }
    ],
    "projects": [
        {
            "name": "Job Hunter",
            "organization": "Personal",
            "type": "Personal",
            "year": 2025,
        }
    ],
    "educations": [
        {
            "course": "Software Engineering",
            "institution": "Example University",
            "period": "2020-2024",
        }
    ],
}


class FakeCollector:
    def __init__(self):
        self.job = Job(
            id="kb-job-1",
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

    def fetch_jobs(self):
        return [self.job]


def write_setup(tmp_path, profile):
    config_path = tmp_path / "config.yaml"
    profile_path = tmp_path / "profile.json"

    config_path.write_text(CONFIG, encoding="utf-8")
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False),
        encoding="utf-8",
    )

    return config_path, profile_path


def knowledge_snapshot(database):
    with database.connect() as conn:
        documents = conn.execute(
            """
            SELECT id, source_type, source_hash, profile_version
            FROM knowledge_document
            ORDER BY id
            """
        ).fetchall()
        chunks = conn.execute(
            """
            SELECT id, document_id, position, content_hash
            FROM knowledge_chunk
            ORDER BY id
            """
        ).fetchall()

    return documents, chunks


def test_bootstrap_persists_candidate_knowledge_base(tmp_path):
    config_path, profile_path = write_setup(tmp_path, PROFILE_V1)

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
    )

    repository = KnowledgeRepository(runner.job_repository.database)
    documents = repository.list_documents(PROFILE_V1["id"])

    assert {document.source_type for document in documents} == {
        "experience",
        "project",
        "education",
        "skills",
    }
    assert all(
        document.candidate_id == PROFILE_V1["id"]
        for document in documents
    )

    chunk_count = 0
    for document in documents:
        chunks = repository.list_chunks(document.id)
        assert chunks
        assert [chunk.position for chunk in chunks] == list(
            range(len(chunks))
        )
        chunk_count += len(chunks)

    assert chunk_count > 0


def test_repeated_bootstrap_does_not_duplicate_knowledge(tmp_path):
    config_path, profile_path = write_setup(tmp_path, PROFILE_V1)
    db_path = tmp_path / "job_hunter.db"

    first_runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=db_path,
    )
    first_snapshot = knowledge_snapshot(first_runner.job_repository.database)

    second_runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=db_path,
    )
    second_snapshot = knowledge_snapshot(
        second_runner.job_repository.database
    )

    assert second_snapshot == first_snapshot


def test_profile_change_updates_knowledge_incrementally(tmp_path):
    config_path, profile_path = write_setup(tmp_path, PROFILE_V1)
    db_path = tmp_path / "job_hunter.db"

    first_runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=db_path,
    )
    documents_before, chunks_before = knowledge_snapshot(
        first_runner.job_repository.database
    )

    changed_profile = dict(PROFILE_V1)
    changed_profile["experiences"] = [
        {
            "company": "Acme",
            "role": "Developer",
            "period": "2024-2025",
            "responsibilities": "Built APIs and dashboards.",
        }
    ]
    profile_path.write_text(
        json.dumps(changed_profile, ensure_ascii=False),
        encoding="utf-8",
    )

    second_runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=db_path,
    )
    documents_after, chunks_after = knowledge_snapshot(
        second_runner.job_repository.database
    )

    assert len(documents_after) == len(documents_before)
    assert {row[0] for row in documents_after} == {
        row[0] for row in documents_before
    }
    assert {row[1] for row in documents_after} == {
        row[1] for row in documents_before
    }

    changed_source_hashes = {
        row[0]
        for row in documents_after
        if row[2]
        != next(
            before[2]
            for before in documents_before
            if before[0] == row[0]
        )
    }
    changed_types = {
        row[1]
        for row in documents_after
        if row[0] in changed_source_hashes
    }
    assert changed_types == {"experience"}

    unchanged_chunk_ids = {
        row[0]
        for row in chunks_before
        if row[1]
        not in {
            document[0]
            for document in documents_after
            if document[0] in changed_source_hashes
        }
    }
    assert unchanged_chunk_ids <= {row[0] for row in chunks_after}


def test_run_once_does_not_alter_knowledge_or_scoring(tmp_path):
    config_path, profile_path = write_setup(tmp_path, PROFILE_V1)
    collector = FakeCollector()

    runner = build_application(
        config_path=config_path,
        profile_path=profile_path,
        db_path=tmp_path / "job_hunter.db",
        collector=collector,
    )
    knowledge_before = knowledge_snapshot(runner.job_repository.database)

    result = runner.run_once()

    assert result.succeeded == 1
    assert knowledge_snapshot(runner.job_repository.database) == (
        knowledge_before
    )

    requirements = RequirementExtractor().extract(
        collector.job.id,
        collector.job.description,
    )
    expected = JobAnalyzer().analyze(
        profile=runner.profile,
        job=collector.job,
        requirements=requirements,
    )

    with runner.job_repository.database.connect() as conn:
        row = conn.execute(
            """
            SELECT compatibility_score, hard_blocker, classification,
                   match_status
            FROM job_analysis
            WHERE job_id = ?
            """,
            (collector.job.id,),
        ).fetchone()

    assert row is not None
    assert row[0] == expected.compatibility_score
    assert row[1] == int(expected.hard_blocker)
    assert row[2] == expected.classification
    assert row[3] == expected.match_status
