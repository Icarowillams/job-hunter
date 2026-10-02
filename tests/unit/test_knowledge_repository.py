import sqlite3

import pytest

from src.domain.models import CandidateProfile
from src.infrastructure.candidate_profile_repository import (
    CandidateProfileRepository,
)
from src.infrastructure.database import Database
from src.infrastructure.knowledge_repository import KnowledgeRepository
from src.knowledge.chunker import KnowledgeChunker
from src.knowledge.document_builder import CandidateKnowledgeDocumentBuilder
from src.knowledge.hashing import profile_content_version


def build_profile(**overrides):
    data = {
        "id": "candidate-1",
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
                "organization": "Acme",
                "type": "Personal",
                "year": 2024,
            }
        ],
        "educations": [
            {
                "course": "Software Engineering",
                "institution": "Example University",
                "period": "2020-2024",
            }
        ],
        "skills": ["Python", "SQL"],
    }
    data.update(overrides)
    return CandidateProfile(**data)


def build_knowledge(profile):
    documents = CandidateKnowledgeDocumentBuilder().build(profile)
    chunker = KnowledgeChunker()
    chunks = [
        chunk
        for document in documents
        for chunk in chunker.chunk(document)
    ]
    return documents, chunks


def sync(repository, profile):
    documents, chunks = build_knowledge(profile)
    return (
        repository.sync(profile.id, documents, chunks),
        documents,
        chunks,
    )


def document_source_hash(profile, source_type):
    documents, _ = build_knowledge(profile)
    return next(
        document.source_hash
        for document in documents
        if document.source_type == source_type
    )


def chunk_ids_by_source_type(repository, candidate_id):
    return {
        document.source_type: [
            chunk.id
            for chunk in repository.list_chunks(document.id)
        ]
        for document in repository.list_documents(candidate_id)
    }


def count(database, table):
    with database.connect() as conn:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]


@pytest.fixture
def database(tmp_path):
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def repository(database):
    return KnowledgeRepository(database)


@pytest.fixture
def profile(database):
    profile = build_profile()
    CandidateProfileRepository(database).save(profile)
    return profile


def test_sync_persists_documents_and_chunks(repository, database, profile):
    result, documents, _ = sync(repository, profile)

    assert result.created == 4
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.removed == 0

    stored = repository.list_documents(profile.id)
    assert len(stored) == len(documents)
    assert {
        document.source_type for document in stored
    } == {"experience", "project", "education", "skills"}
    assert {document.source_hash for document in stored} == {
        document.source_hash for document in documents
    }
    assert {
        document.profile_version for document in stored
    } == {profile_content_version(profile)}

    skills_document = next(
        document
        for document in stored
        if document.source_type == "skills"
    )
    stored_chunks = repository.list_chunks(skills_document.id)
    assert stored_chunks
    assert [chunk.position for chunk in stored_chunks] == list(
        range(len(stored_chunks))
    )
    assert stored_chunks[0].text == skills_document.content
    assert stored_chunks[0].document_id == skills_document.id
    assert count(database, "knowledge_chunk") > 0


def test_sync_is_idempotent(repository, database, profile):
    sync(repository, profile)
    documents_after_first = count(database, "knowledge_document")
    chunks_after_first = count(database, "knowledge_chunk")

    result, _, _ = sync(repository, profile)

    assert result.created == 0
    assert result.updated == 0
    assert result.removed == 0
    assert result.unchanged == 4
    assert count(database, "knowledge_document") == documents_after_first
    assert count(database, "knowledge_chunk") == chunks_after_first


def test_repeated_rebuild_does_not_duplicate_rows(
    repository,
    database,
    profile,
):
    for _ in range(3):
        sync(repository, profile)

    assert count(database, "knowledge_document") == 4

    with database.connect() as conn:
        document_ids = conn.execute(
            "SELECT id FROM knowledge_document"
        ).fetchall()
        chunk_ids = conn.execute(
            "SELECT id FROM knowledge_chunk"
        ).fetchall()

    assert len(document_ids) == len(set(document_ids))
    assert len(chunk_ids) == len(set(chunk_ids))


def test_changed_content_updates_only_the_affected_document(
    repository,
    database,
    profile,
):
    sync(repository, profile)
    original_chunks = chunk_ids_by_source_type(repository, profile.id)

    changed_profile = build_profile(
        experiences=[
            {
                "company": "Acme",
                "role": "Developer",
                "period": "2024-2025",
                "responsibilities": "Built APIs and dashboards.",
            }
        ],
    )
    CandidateProfileRepository(database).save(changed_profile)
    result, documents, _ = sync(repository, changed_profile)

    assert result.created == 0
    assert result.removed == 0

    stored = {
        document.source_type: document
        for document in repository.list_documents(profile.id)
    }
    experience = next(
        document
        for document in documents
        if document.source_type == "experience"
    )
    assert stored["experience"].source_hash == experience.source_hash
    assert "dashboards" in stored["experience"].content
    assert stored["experience"].profile_version == experience.profile_version

    assert stored["skills"].source_hash == document_source_hash(
        profile, "skills"
    )

    current_chunks = chunk_ids_by_source_type(repository, profile.id)
    assert current_chunks["experience"] != original_chunks["experience"]
    for source_type in ("project", "education", "skills"):
        assert current_chunks[source_type] == original_chunks[source_type]


def test_skills_change_updates_profile_version_of_all_documents(
    repository,
    database,
    profile,
):
    sync(repository, profile)
    original_chunks = chunk_ids_by_source_type(repository, profile.id)

    changed_profile = build_profile(skills=["Python", "SQL", "Docker"])
    CandidateProfileRepository(database).save(changed_profile)
    result, _, _ = sync(repository, changed_profile)

    assert result.created == 0
    assert result.removed == 0
    assert result.unchanged == 0

    stored = {
        document.source_type: document
        for document in repository.list_documents(profile.id)
    }
    assert "Docker" in stored["skills"].content
    assert stored["project"].profile_version == profile_content_version(
        changed_profile
    )

    current_chunks = chunk_ids_by_source_type(repository, profile.id)
    assert current_chunks["skills"] != original_chunks["skills"]
    for source_type in ("experience", "project", "education"):
        assert current_chunks[source_type] == original_chunks[source_type]


def test_rebuild_removes_documents_missing_from_the_new_snapshot(
    repository,
    database,
    profile,
):
    sync(repository, profile)
    project_document = next(
        document
        for document in repository.list_documents(profile.id)
        if document.source_type == "project"
    )
    assert repository.list_chunks(project_document.id)

    changed_profile = build_profile(projects=[])
    CandidateProfileRepository(database).save(changed_profile)
    result, _, _ = sync(repository, changed_profile)

    assert result.removed == 1
    assert result.created == 0

    stored = repository.list_documents(profile.id)
    assert {document.source_type for document in stored} == {
        "experience",
        "education",
        "skills",
    }
    assert repository.list_chunks(project_document.id) == []
    assert count(database, "knowledge_document") == 3


def test_sync_scopes_reconciliation_to_the_given_candidate(
    repository,
    database,
    profile,
):
    other_profile = build_profile(id="candidate-2")
    CandidateProfileRepository(database).save(other_profile)

    sync(repository, profile)
    sync(repository, other_profile)
    assert count(database, "knowledge_document") == 8

    changed_profile = build_profile(projects=[])
    CandidateProfileRepository(database).save(changed_profile)
    sync(repository, changed_profile)

    assert len(repository.list_documents(profile.id)) == 3
    assert len(repository.list_documents(other_profile.id)) == 4


def test_sync_requires_an_existing_candidate_profile(repository):
    unsaved_profile = build_profile(id="missing-candidate")
    documents, chunks = build_knowledge(unsaved_profile)

    with pytest.raises(sqlite3.IntegrityError):
        repository.sync(unsaved_profile.id, documents, chunks)


def test_list_documents_and_chunks_return_empty_for_unknown_ids(repository):
    assert repository.list_documents("unknown-candidate") == []
    assert repository.list_chunks("unknown-document") == []
