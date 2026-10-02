from src.analysis.job_analyzer import JobAnalyzer
from src.domain.enums import MatchStatus
from src.domain.models import CandidateProfile, Job, JobRequirement
from src.extraction.requirement_extractor import RequirementExtractor


def test_deterministic_job_analysis_flow():
    job = Job(
        id="job-java-backend",
        source="test",
        title="Backend Developer",
        company="Example",
        description=(
            "Requisitos obrigatórios:\n"
            "Conhecimentos sólidos em Java 17, Spring e PostgreSQL.\n"
            "Experiência com Git e SQL.\n\n"
            "Diferenciais:\n"
            "Docker e Azure."
        ),
    )
    profile = CandidateProfile(
        id="candidate-test",
        skills=["Git", "SQL"],
    )

    requirements = RequirementExtractor().extract(job.id, job.description)
    by_name = {requirement.name: requirement for requirement in requirements}

    assert set(by_name) == {
        "java",
        "spring",
        "postgresql",
        "git",
        "sql",
        "docker",
        "azure",
    }
    assert {
        name for name, requirement in by_name.items() if requirement.mandatory
    } == {"java", "spring", "postgresql", "git", "sql"}
    assert {
        name for name, requirement in by_name.items() if not requirement.mandatory
    } == {"docker", "azure"}

    analysis = JobAnalyzer().analyze(profile, job, requirements)

    assert analysis.breakdown["requirements"] == {
        "java": MatchStatus.MISSING,
        "spring": MatchStatus.MISSING,
        "postgresql": MatchStatus.MISSING,
        "git": MatchStatus.MATCHED,
        "sql": MatchStatus.MATCHED,
        "docker": MatchStatus.UNKNOWN,
        "azure": MatchStatus.UNKNOWN,
    }
    assert analysis.compatibility_score == 33
    assert analysis.hard_blocker is True
    assert analysis.match_status == MatchStatus.MISSING.value
    assert analysis.classification == "REVIEW"
    assert set(analysis.unknown_requirements) == {"docker", "azure"}
    assert set(analysis.gaps) == {"java", "spring", "postgresql"}


def test_javascript_does_not_satisfy_mandatory_java_requirement():
    profile = CandidateProfile(id="candidate-javascript", skills=["JavaScript"])
    job = Job(
        id="job-java-only",
        source="test",
        title="Java Developer",
        company="Example",
        description="Java developer",
    )
    java_requirement = JobRequirement(
        id="req-java",
        job_id=job.id,
        name="Java",
        category="skill",
        mandatory=True,
        extraction_confidence=0.95,
    )

    analysis = JobAnalyzer().analyze(profile, job, [java_requirement])

    assert analysis.breakdown["requirements"]["Java"] == MatchStatus.MISSING
    assert analysis.compatibility_score == 0
    assert analysis.hard_blocker is True
    assert analysis.match_status == MatchStatus.MISSING.value
    assert "Java" in analysis.gaps
