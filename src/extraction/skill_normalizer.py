import re
from typing import Dict, Optional


class SkillNormalizer:
    """
    Normalizes technology/skill names while avoiding false positives.

    Examples:
        React Native -> react_native
        React.js     -> react
        JavaScript   -> javascript
        JS           -> javascript
    """

    DEFAULT_ALIASES: Dict[str, str] = {
        "js": "javascript",
        "javascript": "javascript",
        "javascript.js": "javascript",
        "node": "node.js",
        "nodejs": "node.js",
        "node.js": "node.js",
        "ts": "typescript",
        "typescript": "typescript",
        "react.js": "react",
        "reactjs": "react",
        "react": "react",
        "react native": "react_native",
        "react-native": "react_native",
        "reactnative": "react_native",
        "py": "python",
        "python": "python",
        "python3": "python",
        "postgres": "postgresql",
        "postgresql": "postgresql",
        "sql": "sql",
        "docker": "docker",
        "git": "git",
        "github": "github",
    }

    def __init__(self, aliases: Optional[Dict[str, str]] = None):
        self.aliases = dict(self.DEFAULT_ALIASES)

        if aliases:
            for key, value in aliases.items():
                self.aliases[self._clean(key)] = self._clean(value)

    @staticmethod
    def _clean(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"\s+", " ", value)
        return value

    def normalize(self, skill: str) -> str:
        """
        Return the canonical representation of a skill.

        Unknown skills are normalized conservatively instead of being
        incorrectly mapped to another technology.
        """
        if not isinstance(skill, str):
            raise TypeError("skill must be a string")

        cleaned = self._clean(skill)

        if not cleaned:
            return ""

        return self.aliases.get(cleaned, cleaned)

    def normalize_many(self, skills: list[str]) -> list[str]:
        """
        Normalize a collection of skills and remove duplicates while
        preserving their original order.
        """
        result = []
        seen = set()

        for skill in skills:
            normalized = self.normalize(skill)

            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)

        return result

    def are_equivalent(self, first: str, second: str) -> bool:
        """
        Check whether two skill names represent the same canonical skill.
        """
        return self.normalize(first) == self.normalize(second)
