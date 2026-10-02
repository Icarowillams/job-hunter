from src.domain.models import CandidateProfile
from src.infrastructure.profile_loader import ProfileLoader


def test_load_candidate_profile():
    loader = ProfileLoader()

    profile = loader.load("tests/fixtures/profile.json")

    assert isinstance(profile, CandidateProfile)
    assert profile.id == "sample-candidate"

    assert "node.js" in profile.skills
    assert "typescript" in profile.skills
    assert "deno" in profile.skills

    assert "Desenvolvedor Backend Júnior" in profile.target_roles

    assert len(profile.experiences) >= 1
    assert len(profile.educations) >= 1
    assert len(profile.languages) == 1


def test_profile_file_is_utf8():
    loader = ProfileLoader()

    profile = loader.load("tests/fixtures/profile.json")

    assert profile.location == "Olinda - PE"
    assert profile.languages[0]["language"] == "Inglês"
    assert profile.languages[0]["level"] == "B1"