
import re
import uuid
from typing import List

from src.domain.models import JobRequirement
from src.extraction.skill_normalizer import SkillNormalizer


class RequirementExtractor:
    """
    Extracts technical and professional requirements from job descriptions.

    The extractor is intentionally rule-based in the current lightweight
    architecture. Semantic/LLM extraction can be added in future phases.
    """

    SECTION_HEADERS = (
        "requisitos",
        "requisitos técnicos",
        "requisitos tecnicos",
        "qualificações",
        "qualificacoes",
        "qualificações técnicas",
        "qualificacoes tecnicas",
        "conhecimentos",
        "competências",
        "competencias",
        "skills",
        "requirements",
        "technical requirements",
    )

    MANDATORY_PATTERNS = (
        r"\bobrigat[oó]rio\b",
        r"\bobrigat[oó]ria\b",
        r"\bnecess[aá]rio\b",
        r"\bnecess[aá]ria\b",
        r"\brequisito\b",
        r"\bimprescind[ií]vel\b",
        r"\bmust have\b",
        r"\brequired\b",
    )

    OPTIONAL_PATTERNS = (
        r"\bdiferencial\b",
        r"\bdesej[aá]vel\b",
        r"\bser[aá] um diferencial\b",
        r"\bnice to have\b",
        r"\bpreferred\b",
        r"\bplus\b",
    )

    DEFAULT_SKILLS = (
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "react native",
        "node.js",
        "sql",
        "postgresql",
        "mysql",
        "docker",
        "git",
        "github",
        "aws",
        "azure",
        "gcp",
        "html",
        "css",
        "django",
        "flask",
        "fastapi",
        "spring",
        "c#",
        ".net",
        "php",
        "ruby",
        "go",
        "kotlin",
        "swift",
    )

    def __init__(self, skill_normalizer: SkillNormalizer | None = None):
        self.skill_normalizer = skill_normalizer or SkillNormalizer()

    def extract(self, job_id: str, description: str) -> List[JobRequirement]:
        """
        Extract requirements from a job description.
        """
        if not isinstance(description, str):
            raise TypeError("description must be a string")

        if not description.strip():
            return []

        description = self._normalize_text(description)

        requirements: List[JobRequirement] = []

        for skill in self._find_skills(description):
            context = self._skill_context(description, skill)

            mandatory = self._is_mandatory(context)
            category = self._classify(skill)

            requirements.append(
                JobRequirement(
                    id=str(uuid.uuid4()),
                    job_id=job_id,
                    name=self.skill_normalizer.normalize(skill),
                    category=category,
                    mandatory=mandatory,
                    extraction_confidence=self._confidence(skill, context),
                )
            )

        return self._deduplicate(requirements)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text used by the rule-based extractor.

        This keeps the original characters but normalizes Unicode
        representation so accented Portuguese text can be matched
        consistently.
        """
        import unicodedata

        return unicodedata.normalize("NFC", text)

    def _find_skills(self, description: str) -> List[str]:
        """
        Find known skills using word-boundary-aware matching.

        Compound skills are matched before their component skills. When a
        compound skill contains another known skill, the component skill is
        suppressed if both refer to the same occurrence.

        Examples:
            React Native -> react native only
            JavaScript   -> javascript, not java
            Node.js      -> node.js
        """
        found: List[str] = []

        normalized_description = description.lower()

        skills = sorted(
            self.DEFAULT_SKILLS,
            key=len,
            reverse=True,
        )

        occupied_spans: List[tuple[int, int]] = []

        for skill in skills:
            pattern = self._skill_pattern(skill)

            for match in re.finditer(
                pattern,
                normalized_description,
                flags=re.IGNORECASE,
            ):
                span = match.span()

                # If this occurrence overlaps a previously matched longer
                # skill, it is a component of that compound skill and must
                # not be emitted independently.
                if any(
                    self._spans_overlap(span, occupied)
                    for occupied in occupied_spans
                ):
                    continue

                found.append(skill)
                occupied_spans.append(span)

        return found

    @staticmethod
    def _spans_overlap(
        first: tuple[int, int],
        second: tuple[int, int],
    ) -> bool:
        return first[0] < second[1] and second[0] < first[1]

    @staticmethod
    def _skill_pattern(skill: str) -> str:
        escaped = re.escape(skill)

        # Technologies containing punctuation such as C# or .NET need
        # a slightly more permissive boundary than ordinary words.
        if skill in {"c#", ".net", "node.js"}:
            return rf"(?<!\w){escaped}(?!\w)"

        return rf"(?<!\w){escaped}(?!\w)"

    @staticmethod
    def _skill_context(description: str, skill: str) -> str:
        pattern = RequirementExtractor._skill_pattern(skill)

        match = re.search(
            pattern,
            description,
            flags=re.IGNORECASE,
        )

        if not match:
            return description

        start = max(0, match.start() - 150)
        end = min(len(description), match.end() + 150)

        return description[start:end]

    def _is_mandatory(self, context: str) -> bool:
        lowered = context.lower()

        if any(
            re.search(pattern, lowered)
            for pattern in self.MANDATORY_PATTERNS
        ):
            return True

        if any(
            re.search(pattern, lowered)
            for pattern in self.OPTIONAL_PATTERNS
        ):
            return False

        # A technical skill discovered in a requirements section is
        # considered a requirement, but not automatically mandatory.
        return False

    @staticmethod
    def _classify(skill: str) -> str:
        technical = {
            "python",
            "java",
            "javascript",
            "typescript",
            "react",
            "react native",
            "node.js",
            "sql",
            "postgresql",
            "mysql",
            "docker",
            "git",
            "github",
            "aws",
            "azure",
            "gcp",
            "html",
            "css",
            "django",
            "flask",
            "fastapi",
            "spring",
            "c#",
            ".net",
            "php",
            "ruby",
            "go",
            "kotlin",
            "swift",
        }

        if skill.lower() in technical:
            return "technical"

        return "other"

    @staticmethod
    def _confidence(skill: str, context: str) -> float:
        """
        Confidence score for the rule-based extraction.

        Explicit requirement language receives higher confidence.
        """
        lowered = context.lower()

        if any(
            re.search(pattern, lowered)
            for pattern in RequirementExtractor.MANDATORY_PATTERNS
        ):
            return 0.95

        if any(
            re.search(pattern, lowered)
            for pattern in RequirementExtractor.OPTIONAL_PATTERNS
        ):
            return 0.90

        return 0.80

    @staticmethod
    def _deduplicate(
        requirements: List[JobRequirement],
    ) -> List[JobRequirement]:
        unique = {}

        for requirement in requirements:
            key = (
                requirement.name,
                requirement.category,
            )

            if key not in unique:
                unique[key] = requirement
            elif requirement.mandatory and not unique[key].mandatory:
                unique[key] = requirement

        return list(unique.values())
