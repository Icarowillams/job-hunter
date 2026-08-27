from src.domain.enums import MatchStatus
from src.scoring.scoring_engine import ScoringEngine


def test_all_matched_requirements_produce_full_score():
    matches = {
        "Python": MatchStatus.MATCHED,
        "React": MatchStatus.MATCHED,
    }

    requirements = {
        "Python": {"mandatory": True},
        "React": {"mandatory": False},
    }

    engine = ScoringEngine()

    result = engine.calculate(matches, requirements)

    assert result["compatibility_score"] == 100
    assert result["hard_blocker"] is False


def test_missing_mandatory_requirement_creates_hard_blocker():
    matches = {
        "Python": MatchStatus.MATCHED,
        "Kubernetes": MatchStatus.MISSING,
    }

    requirements = {
        "Python": {"mandatory": True},
        "Kubernetes": {"mandatory": True},
    }

    engine = ScoringEngine()

    result = engine.calculate(matches, requirements)

    assert result["compatibility_score"] == 50
    assert result["hard_blocker"] is True


def test_unknown_requirement_reduces_confidence_not_compatibility():
    matches = {
        "Python": MatchStatus.MATCHED,
        "AWS": MatchStatus.UNKNOWN,
    }

    requirements = {
        "Python": {"mandatory": True},
        "AWS": {"mandatory": False},
    }

    engine = ScoringEngine()

    result = engine.calculate(matches, requirements)

    assert result["compatibility_score"] == 67
    assert result["confidence_score"] < 100
    assert result["hard_blocker"] is False