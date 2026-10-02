from datetime import datetime, timezone
from uuid import uuid4

from src.analysis.eligibility import EligibilityEvaluator
from src.extraction.requirement_extractor import RequirementExtractor

from src.domain.enums import MatchStatus
from src.domain.models import CandidateProfile, Job, JobAnalysis, JobRequirement
from src.matching.requirement_matcher import RequirementMatcher
from src.scoring.scoring_engine import ScoringEngine


class JobAnalyzer:
    SCORING_VERSION = "v1"
    EXTRACTOR_VERSION = "v1"
    NORMALIZER_VERSION = "v1"

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

        waived = []
        normalizer = self.matcher.normalizer

        for group in RequirementExtractor().extract_alternative_groups(
            job.description or ""
        ):
            normalized_matches = {
                normalizer.normalize(name): name
                for name in matches
            }

            satisfied_normalized = next(
                (
                    normalized_name
                    for normalized_name in group
                    if normalized_name in normalized_matches
                    and matches[normalized_matches[normalized_name]]
                    == MatchStatus.MATCHED
                ),
                None,
            )

            if satisfied_normalized:
                satisfied = normalized_matches[satisfied_normalized]

                for other_normalized in group:
                    if other_normalized == satisfied_normalized:
                        continue

                    other = normalized_matches.get(other_normalized)

                    if other and matches[other] != MatchStatus.MATCHED:
                        del matches[other]
                        waived.append(
                            {
                                "alternative": other,
                                "satisfied_by": satisfied,
                            }
                        )

        requirement_metadata = {
            requirement.name: {
                "mandatory": requirement.mandatory,
            }
            for requirement in requirements
            if requirement.name in matches
        }

        scoring = self.scoring_engine.calculate(
            matches,
            requirement_metadata,
        )

        strengths = [
            name
            for name, status in matches.items()
            if status == MatchStatus.MATCHED
        ]

        gaps = [
            name
            for name, status in matches.items()
            if status == MatchStatus.MISSING
        ]

        unknown_requirements = [
            name
            for name, status in matches.items()
            if status == MatchStatus.UNKNOWN
        ]

        eligibility, eligibility_blocker, resume = (
            EligibilityEvaluator().evaluate(
                profile,
                job,
                requirements,
            )
        )

        hard_blocker = scoring["hard_blocker"] or eligibility_blocker

        classification = (
            "IGNORE"
            if eligibility.get("status") == "rejected"
            else (
                "REVIEW"
                if hard_blocker or scoring["compatibility_score"] < 70
                else "PRIORITY"
            )
        )

        if hard_blocker:
            match_status = MatchStatus.MISSING.value
        elif not requirements:
            match_status = MatchStatus.UNKNOWN.value
        elif unknown_requirements:
            match_status = MatchStatus.PARTIAL.value
        elif gaps:
            match_status = MatchStatus.PARTIAL.value
        else:
            match_status = MatchStatus.MATCHED.value

        breakdown = {
            "requirements": matches,
            "recommended_resume": resume,
        }

        if eligibility:
            breakdown["eligibility"] = eligibility

        if waived:
            breakdown["alternatives_satisfied"] = waived

        return JobAnalysis(
            id=str(uuid4()),
            job_id=job.id,
            compatibility_score=scoring["compatibility_score"],
            priority_score=scoring["compatibility_score"],
            confidence_score=scoring["confidence_score"],
            breakdown=breakdown,
            classification=classification,
            match_status=match_status,
            strengths=strengths,
            gaps=gaps,
            unknown_requirements=unknown_requirements,
            hard_blocker=hard_blocker,
            scoring_version=self.SCORING_VERSION,
            extractor_version=self.EXTRACTOR_VERSION,
            normalizer_version=self.NORMALIZER_VERSION,
            analyzed_at=datetime.now(timezone.utc),
        )
