from src.domain.models import CandidateProfile
from src.knowledge.document_builder import CandidateKnowledgeDocumentBuilder
from src.knowledge.hashing import content_hash, profile_content_version


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


def documents_for(**overrides):
    return CandidateKnowledgeDocumentBuilder().build(build_profile(**overrides))


def test_simple_candidate_profile_generates_knowledge_documents():
    documents = documents_for()

    assert len(documents) == 4
    assert {document.source_type for document in documents} == {
        "experience",
        "project",
        "education",
        "skills",
    }


def test_experiences_preserve_source_type_and_reference():
    document = next(
        document
        for document in documents_for()
        if document.source_type == "experience"
    )

    assert document.source_ref.startswith("experience:")
    assert document.metadata["source_type"] == "experience"
    assert document.metadata["source_ref"] == document.source_ref


def test_projects_preserve_source_type_and_reference():
    document = next(
        document
        for document in documents_for()
        if document.source_type == "project"
    )

    assert document.source_ref.startswith("project:")
    assert "name: Job Hunter" in document.content


def test_education_is_converted_to_a_document():
    document = next(
        document
        for document in documents_for()
        if document.source_type == "education"
    )

    assert document.source_ref.startswith("education:")
    assert "course: Software Engineering" in document.content


def test_skills_are_represented_without_creating_individual_documents():
    documents = documents_for()
    skill_documents = [
        document for document in documents if document.source_type == "skills"
    ]

    assert len(skill_documents) == 1
    assert skill_documents[0].source_ref == "profile-skills"
    assert skill_documents[0].content == 'skills: ["Python","SQL"]'


def test_documents_have_deterministic_hashes_and_profile_version():
    first, second = documents_for(), documents_for()

    assert [document.source_hash for document in first] == [
        document.source_hash for document in second
    ]
    assert {document.profile_version for document in first} == {
        profile_content_version(build_profile())
    }


def test_same_content_produces_the_same_hash():
    assert content_hash("same content") == content_hash("same content")


def test_different_content_produces_a_different_hash():
    assert content_hash("first content") != content_hash("second content")


def test_builder_does_not_invent_information():
    profile = build_profile(
        experiences=[{"company": "Acme"}],
        projects=[],
        educations=[],
        skills=[],
    )

    documents = CandidateKnowledgeDocumentBuilder().build(profile)

    assert len(documents) == 1
    assert documents[0].content == "company: Acme"
    assert "role:" not in documents[0].content
    assert "skills:" not in documents[0].content


def test_reordering_records_preserves_their_source_references():
    first_experience = {
        "company": "Acme",
        "role": "Developer",
        "period": "2024-2025",
    }
    second_experience = {
        "company": "Beta",
        "role": "Engineer",
        "period": "2023-2024",
    }
    first_project = {
        "name": "Project One",
        "organization": "Acme",
        "year": 2024,
    }
    second_project = {
        "name": "Project Two",
        "organization": "Beta",
        "year": 2023,
    }
    first_education = {
        "course": "Computer Science",
        "institution": "University One",
        "period": "2020-2024",
    }
    second_education = {
        "course": "Systems Analysis",
        "institution": "University Two",
        "period": "2018-2020",
    }

    first = documents_for(
        experiences=[first_experience, second_experience],
        projects=[first_project, second_project],
        educations=[first_education, second_education],
    )
    reordered = documents_for(
        experiences=[second_experience, first_experience],
        projects=[second_project, first_project],
        educations=[second_education, first_education],
    )

    assert {
        document.source_ref for document in first if document.source_type == "experience"
    } == {
        document.source_ref
        for document in reordered
        if document.source_type == "experience"
    }
    assert {
        document.source_ref for document in first if document.source_type == "project"
    } == {
        document.source_ref
        for document in reordered
        if document.source_type == "project"
    }
    assert {
        document.source_ref for document in first if document.source_type == "education"
    } == {
        document.source_ref
        for document in reordered
        if document.source_type == "education"
    }


def test_changing_experience_responsibilities_preserves_identity():
    original = next(
        document
        for document in documents_for()
        if document.source_type == "experience"
    )
    changed = next(
        document
        for document in documents_for(
            experiences=[
                {
                    "company": "Acme",
                    "role": "Developer",
                    "period": "2024-2025",
                    "responsibilities": "Built APIs and dashboards.",
                }
            ]
        )
        if document.source_type == "experience"
    )

    assert changed.source_ref == original.source_ref
    assert changed.id == original.id
    assert changed.source_hash != original.source_hash


def test_changing_experience_evidence_preserves_identity():
    original = next(
        document
        for document in documents_for(
            experiences=[
                {
                    "company": "Acme",
                    "role": "Developer",
                    "period": "2024-2025",
                    "evidence": {"users": 10},
                }
            ]
        )
        if document.source_type == "experience"
    )
    changed = next(
        document
        for document in documents_for(
            experiences=[
                {
                    "company": "Acme",
                    "role": "Developer",
                    "period": "2024-2025",
                    "evidence": {"users": 20},
                }
            ]
        )
        if document.source_type == "experience"
    )

    assert changed.source_ref == original.source_ref
    assert changed.id == original.id
    assert changed.source_hash != original.source_hash


def test_changing_experience_identity_fields_changes_identity():
    original = next(
        document
        for document in documents_for()
        if document.source_type == "experience"
    )
    changed = next(
        document
        for document in documents_for(
            experiences=[
                {
                    "company": "Acme",
                    "role": "Senior Developer",
                    "period": "2024-2025",
                    "responsibilities": "Built APIs.",
                }
            ]
        )
        if document.source_type == "experience"
    )

    assert changed.source_ref != original.source_ref
    assert changed.id != original.id


def test_changing_non_identity_project_content_preserves_identity():
    original = next(
        document
        for document in documents_for(
            projects=[
                {
                    "name": "Job Hunter",
                    "organization": "Acme",
                    "year": 2024,
                    "description": "Initial description.",
                }
            ]
        )
        if document.source_type == "project"
    )
    changed = next(
        document
        for document in documents_for(
            projects=[
                {
                    "name": "Job Hunter",
                    "organization": "Acme",
                    "year": 2024,
                    "description": "Updated description.",
                }
            ]
        )
        if document.source_type == "project"
    )

    assert changed.source_ref == original.source_ref
    assert changed.id == original.id
    assert changed.source_hash != original.source_hash


def test_different_natural_experience_identities_have_different_references():
    documents = documents_for(
        experiences=[
            {"company": "Acme", "role": "Developer", "period": "2024"},
            {"company": "Beta", "role": "Developer", "period": "2024"},
        ]
    )
    references = [
        document.source_ref
        for document in documents
        if document.source_type == "experience"
    ]

    assert len(set(references)) == 2


def test_incomplete_natural_identity_uses_a_deterministic_record_fallback():
    record = {"company": "Acme", "responsibilities": "Built APIs."}
    first = next(
        document
        for document in documents_for(experiences=[record])
        if document.source_type == "experience"
    )
    second = next(
        document
        for document in documents_for(experiences=[record])
        if document.source_type == "experience"
    )

    assert first.source_ref.startswith("experience:")
    assert first.source_ref == second.source_ref


def test_profile_skills_reference_remains_stable_when_skills_change():
    original = next(
        document
        for document in documents_for(skills=["Python"])
        if document.source_type == "skills"
    )
    changed = next(
        document
        for document in documents_for(skills=["Python", "SQL"])
        if document.source_type == "skills"
    )

    assert original.source_ref == "profile-skills"
    assert changed.source_ref == original.source_ref
    assert changed.id == original.id
    assert changed.source_hash != original.source_hash
