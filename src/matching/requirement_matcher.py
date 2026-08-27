from src.domain.enums import MatchStatus
from src.domain.models import CandidateProfile, JobRequirement
from src.extraction.skill_normalizer import SkillNormalizer


class RequirementMatcher:
    def __init__(self, normalizer=None):
        self.normalizer = normalizer or SkillNormalizer()

    def match(
        self,
        profile: CandidateProfile,
        requirements: list[JobRequirement],
    ) -> dict[str, MatchStatus]:
        normalized_profile_skills = {
            self.normalizer.normalize(skill)
            for skill in profile.skills
        }

        normalized_explicit_gaps = {
            self.normalizer.normalize(skill)
            for skill in profile.explicit_gaps
        }

        results = {}

        for requirement in requirements:
            normalized_requirement = self.normalizer.normalize(requirement.name)

            if normalized_requirement in normalized_profile_skills:
                results[requirement.name] = MatchStatus.MATCHED

            elif normalized_requirement in normalized_explicit_gaps:
                results[requirement.name] = MatchStatus.MISSING

            elif requirement.mandatory:
                results[requirement.name] = MatchStatus.MISSING

            else:
                results[requirement.name] = MatchStatus.UNKNOWN

        return results