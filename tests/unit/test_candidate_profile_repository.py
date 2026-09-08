from datetime import datetime
from src.domain.models import CandidateProfile
from src.infrastructure.candidate_profile_repository import (
    CandidateProfileRepository,
)
from src.infrastructure.database import Database


def test_save_and_get_candidate_profile(tmp_path):
    database = Database(str(tmp_path / "job_hunter.db"))
    repository = CandidateProfileRepository(database)

    profile = CandidateProfile(
        id="candidate-1",
        target_roles=["Software Engineer", "Backend Developer"],
        desired_seniority=["junior"],
        location="Olinda - PE",
        work_modes=["remote"],
        salary_expectation="R$ 3.000",
        relocation_availability=True,
        skills=["Python", "React", "TypeScript"],
        explicit_gaps=["Kubernetes"],
        experiences=[
            {
                "company": "Acme",
                "role": "Software Developer",
            }
        ],
        educations=[
            {
                "course": "Engenharia de Software",
            }
        ],
        projects=[
            {
                "name": "Job Hunter",
            }
        ],
        languages=[
            {
                "language": "Português",
                "level": "native",
            }
        ],
        certifications=["AWS Cloud Practitioner"],
        preferences={
            "company_size": "medium",
        },
        restrictions=["onsite"],
    )

    repository.save(profile)

    result = repository.get_by_id("candidate-1")

    assert result is not None
    assert result.id == profile.id
    assert result.target_roles == profile.target_roles
    assert result.desired_seniority == profile.desired_seniority
    assert result.location == profile.location
    assert result.work_modes == profile.work_modes
    assert result.salary_expectation == profile.salary_expectation
    assert result.relocation_availability is True
    assert result.skills == profile.skills
    assert result.explicit_gaps == profile.explicit_gaps
    assert result.experiences == profile.experiences
    assert result.educations == profile.educations
    assert result.projects == profile.projects
    assert result.languages == profile.languages
    assert result.certifications == profile.certifications
    assert result.preferences == profile.preferences
    assert result.restrictions == profile.restrictions

def test_get_by_id_returns_none_when_profile_does_not_exist(tmp_path):
    database = Database(str(tmp_path / "job_hunter.db"))
    repository = CandidateProfileRepository(database)

    result = repository.get_by_id("missing")

    assert result is None
    from datetime import datetime

def test_save_and_get_preserves_datetime_fields(tmp_path):
    database = Database(str(tmp_path / "job_hunter.db"))
    repository = CandidateProfileRepository(database)

    profile = CandidateProfile(
        id="candidate-datetime",
        skills=["Python"],
        availability_date=datetime(2026, 9, 1, 10, 30),
        updated_at=datetime(2026, 8, 28, 12, 0),
    )

    repository.save(profile)

    result = repository.get_by_id(profile.id)

    assert result is not None
    assert result.availability_date == profile.availability_date
    assert result.updated_at == profile.updated_at
