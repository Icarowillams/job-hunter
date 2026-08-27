from src.domain.enums import MatchStatus


class ScoringEngine:
    MANDATORY_WEIGHT = 2
    OPTIONAL_WEIGHT = 1

    def calculate(
        self,
        matches: dict[str, MatchStatus],
        requirements: dict[str, dict],
    ) -> dict:
        total_weight = 0
        matched_weight = 0
        unknown_weight = 0
        hard_blocker = False

        for name, requirement in requirements.items():
            mandatory = requirement.get("mandatory", False)
            weight = (
                self.MANDATORY_WEIGHT
                if mandatory
                else self.OPTIONAL_WEIGHT
            )

            total_weight += weight

            status = matches.get(name, MatchStatus.UNKNOWN)

            if status == MatchStatus.MATCHED:
                matched_weight += weight

            elif status == MatchStatus.MISSING:
                if mandatory:
                    hard_blocker = True

            elif status == MatchStatus.UNKNOWN:
                unknown_weight += weight

        compatibility_score = (
            round((matched_weight / total_weight) * 100)
            if total_weight
            else 0
        )

        confidence_score = (
            round(
                ((total_weight - unknown_weight) / total_weight) * 100
            )
            if total_weight
            else 0
        )

        return {
            "compatibility_score": compatibility_score,
            "confidence_score": confidence_score,
            "hard_blocker": hard_blocker,
        }