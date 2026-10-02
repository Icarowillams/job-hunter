
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
        r"\bobrigat[oó]ri[oa]s?\b",
        r"\bnecess[aá]ri[oa]s?\b",
        r"\bobrigat[oó]rio\b",
        r"\bobrigat[oó]ria\b",
        r"\bnecess[aá]rio\b",
        r"\bnecess[aá]ria\b",
        r"\brequisito\b",
        r"\bimprescind[ií]vel\b",
        r"\bmust have\b",
        r"\brequired\b",
        r"\bis\s+necessary\b",
        r"\bis\s+mandatory\b",
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
        "deno",
        "nodejs",
        "react.js",
        "reactjs",
        "ts",
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

        mandatory_section = False
        for context in self.clauses(description):
            is_section, section_is_mandatory = self._section_context(context)
            if is_section:
                mandatory_section = section_is_mandatory

            # Explicitly waived technologies are not requirements and must not lower the score.
            if re.search(r"\b(n[ãa]o\s+(?:[ée]\s+)?(?:necess[aá]ri[oa]|obrigat[oó]ri[oa]|exigid[oa]|precisa|exigimos|requer)|not\s+(?:required|necessary|needed)|sem\s+necessidade|no\s+need)\b", context, re.I):
                continue
            for skill in self._find_skills(context):
                requirements.append(JobRequirement(
                    id=str(uuid.uuid4()), job_id=job_id,
                    name=self.skill_normalizer.normalize(skill),
                    category=self._classify(skill), mandatory=(
                        self._is_mandatory(context, mandatory_section)
                    ),
                    extraction_confidence=self._confidence(skill, context),
                ))

        return self._deduplicate(requirements)

    @staticmethod
    def clauses(description):
        # Preserve punctuation within Node.js/.NET; split at sentence boundaries, not every dot.
        return [part.strip() for part in re.split(r"[;\n!?•]|(?<=\.)\s+|\b(?:mas|porém|however|but)\b", description, flags=re.I) if part.strip()]

    def extract_alternative_groups(self, description):
        groups = []
        skills = '|'.join(re.escape(skill) for skill in sorted(self.DEFAULT_SKILLS, key=len, reverse=True))
        pattern = re.compile(r'(?<!\w)('+skills+r')\s+(?:ou|or)\s+('+skills+r')(?!\w)', re.I)
        for clause in self.clauses(description):
            for match in pattern.finditer(clause):
                a,b = match.groups()
                # If the skill is also explicitly listed elsewhere, do not waive that separate requirement.
                if any(len(re.findall(self._skill_pattern(x), description, re.I)) != 1 for x in (a,b)):
                    continue
                # Nested/multi-way alternatives are deliberately not simplified.
                if re.search(r'\b(?:ou|or)\s*$', clause[:match.start()], re.I) or re.match(r'\s+(?:ou|or)\b', clause[match.end():], re.I):
                    continue
                pair = [self.skill_normalizer.normalize(a), self.skill_normalizer.normalize(b)]
                if pair[0] != pair[1] and pair not in groups:
                    groups.append(pair)
        return groups

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

    @staticmethod
    def _fold_accents(text: str) -> str:
        import unicodedata

        return "".join(
            char for char in unicodedata.normalize("NFD", text)
            if not unicodedata.combining(char)
        ).lower()

    @classmethod
    def _section_context(cls, context: str) -> tuple[bool, bool]:
        folded = cls._fold_accents(context).strip()
        headers = (
            "requisitos", "requisitos tecnicos", "requisitos obrigatorios",
            "requisitos tecnicos obrigatorios", "requisitos desejaveis",
            "requisitos tecnicos desejaveis", "qualificacoes",
            "qualificacoes tecnicas", "qualificacoes obrigatorias",
            "qualificacoes desejaveis",
            "conhecimentos", "competencias", "skills", "requirements",
            "technical requirements", "mandatory requirements",
            "required qualifications",
            "diferenciais", "desejavel", "preferred", "nice to have",
            "beneficios", "sobre a vaga", "responsabilidades",
        )
        # A heading must stand alone or end with a colon. Prefix matching alone
        # mistakes requirement prose such as "Conhecimentos sólidos em Java" for
        # a new section and prematurely clears the section context.
        heading = folded.split(":", 1)[0].strip()
        if heading not in headers:
            return False, False

        is_mandatory = heading in {
            "requisitos obrigatorios", "requisitos tecnicos obrigatorios",
            "qualificacoes obrigatorias", "mandatory requirements",
            "required qualifications",
        } or (
            heading.startswith(("requisitos ", "qualificacoes ", "requirements ", "technical requirements "))
            and any(token in heading.split() for token in ("obrigatorios", "obrigatorias", "necessarios", "necessarias", "mandatory", "required"))
        )
        is_optional = any(
            re.search(pattern, heading)
            for pattern in (
                r"\bdiferencial\b", r"\bdesejavel\b",
                r"\bpreferred\b", r"\bnice to have\b",
            )
        )
        return True, is_mandatory and not is_optional

    def _is_mandatory(self, context: str, mandatory_section: bool = False) -> bool:
        lowered = context.lower()

        if any(
            re.search(pattern, lowered)
            for pattern in self.OPTIONAL_PATTERNS
        ):
            return False

        if any(
            re.search(pattern, lowered)
            for pattern in self.MANDATORY_PATTERNS
        ):
            return True

        if mandatory_section:
            return True

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
        "deno",
        "nodejs",
        "react.js",
        "reactjs",
        "ts",
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
