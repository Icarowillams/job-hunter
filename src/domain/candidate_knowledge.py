from typing import Any

from pydantic import BaseModel, Field


DOCUMENT_SCHEMA_VERSION = "v1"


class CandidateKnowledgeDocument(BaseModel):
    """A traceable knowledge source derived from a candidate profile."""

    id: str
    candidate_id: str
    source_type: str
    source_ref: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_hash: str
    profile_version: str
    document_schema_version: str = DOCUMENT_SCHEMA_VERSION


class KnowledgeChunk(BaseModel):
    """A deterministic, persistable segment of a knowledge document."""

    id: str
    document_id: str
    position: int
    text: str
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
