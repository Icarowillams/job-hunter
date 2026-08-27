from uuid import uuid4

from src.domain.models import CandidateProfile, Job, JobAnalysis, JobRequirement
from src.matching.requirement_matcher import RequirementMatcher
from src.scoring.scoring_engine import ScoringEngine


class JobAnalyzer:
    def __init__(
        self,
        matcher: RequirementMatcher | None = None,
        scoring_engine: ScoringEngine | None = None,
    ):
        self.matcher = matcher or RequirementMatcher()
        self.scoring_engine = scoring_engine or ScoringEngine()

    def analyze(
        self,
        profile: CandidateProfile,
        job: Job,
        requirements: list[JobRequirement],
    ) -> JobAnalysis:
        matches = self.matcher.match(profile, requirements)

        requirement_metadata = {
            requirement.name: {
                "mandatory": requirement.mandatory,
            }
            for requirement in requirements
        }

        scoring = self.scoring_engine.calculate(
            matches,
            requirement_metadata,
        )

        strengths = [
            name
            for name, status in matches.items()
            if status.value == "MATCHED"
        ]

        gaps = [
            name
            for name, status in matches.items()
            if status.value == "MISSING"
        ]

        unknown_requirements = [
            name
            for name, status in matches.items()
            if status.value == "UNKNOWN"
        ]

        return JobAnalysis(
            id=str(uuid4()),
            job_id=job.id,
            compatibility_score=scoring["compatibility_score"],
            priority_score=scoring["compatibility_score"],
            confidence_score=scoring["confidence_score"],
            breakdown={
                "requirements": matches,
            },
            strengths=strengths,
            gaps=gaps,
            unknown_requirements=unknown_requirements,
            hard_blocker=scoring["hard_blocker"],
        )