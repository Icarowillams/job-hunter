import json
from pathlib import Path

from src.domain.models import CandidateProfile


class ProfileLoader:
    """Loads and validates a candidate profile from JSON."""

    def load(self, path: str | Path) -> CandidateProfile:
        profile_path = Path(path)

        if not profile_path.exists():
            raise FileNotFoundError(
                f"Candidate profile not found: {profile_path}"
            )

        with profile_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return CandidateProfile.model_validate(data)