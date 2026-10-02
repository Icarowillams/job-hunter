import hashlib
import json
from typing import Any

from src.domain.models import CandidateProfile


PROFILE_KNOWLEDGE_FIELDS = (
    "experiences",
    "projects",
    "educations",
    "skills",
)


def canonical_json(value: Any) -> str:
    """Serialize data consistently for content-based comparisons."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def content_hash(content: str) -> str:
    """Return a stable SHA-256 hash for text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def stable_id(value: Any) -> str:
    """Return a stable identifier derived from canonical structured data."""
    return content_hash(canonical_json(value))


def profile_content_version(profile: CandidateProfile) -> str:
    """Identify the profile content used by the knowledge builder.

    The version intentionally excludes timestamps and fields that do not
    produce documents in this foundation.
    """
    content = {
        field: getattr(profile, field)
        for field in PROFILE_KNOWLEDGE_FIELDS
    }
    return stable_id(content)
