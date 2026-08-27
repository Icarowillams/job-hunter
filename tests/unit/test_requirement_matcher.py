from src.domain.enums import MatchStatus
from src.domain.models import CandidateProfile, JobRequirement
from src.matching.requirement_matcher import RequirementMatcher


def test_matching_skills_are_matched():
    profile = CandidateProfile(
        id="candidate-1",
        skills=["Python", "React", "Docker"],
    )

    requirements = [
        JobRequirement(
            id="req-1",
            job_id="job-1",
            name="Python",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
        JobRequirement(
            id="req-2",
            job_id="job-1",
            name="React",
            category="skill",
            mandatory=False,
            extraction_confidence=0.80,
        ),
    ]

    matcher = RequirementMatcher()

    results = matcher.match(profile, requirements)

    assert results["Python"] == MatchStatus.MATCHED
    assert results["React"] == MatchStatus.MATCHED


def test_missing_skill_is_missing():
    profile = CandidateProfile(
        id="candidate-1",
        skills=["Python"],
    )

    requirements = [
        JobRequirement(
            id="req-1",
            job_id="job-1",
            name="Kubernetes",
            category="skill",
            mandatory=True,
            extraction_confidence=0.95,
        ),
    ]

    matcher = RequirementMatcher()

    results = matcher.match(profile, requirements)

    assert results["Kubernetes"] == MatchStatus.MISSING


def test_unknown_skill_is_unknown():
    profile = CandidateProfile(
        id="candidate-1",
        skills=["Python"],
        explicit_gaps=[],
    )

    requirements = [
        JobRequirement(
            id="req-1",
            job_id="job-1",
            name="AWS",
            category="skill",
            mandatory=False,
            extraction_confidence=0.60,
        ),
    ]

    matcher = RequirementMatcher()

    results = matcher.match(profile, requirements)

    assert results["AWS"] == MatchStatus.UNKNOWN