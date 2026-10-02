import json
from typing import Any

from src.domain.candidate_knowledge import (
    DOCUMENT_SCHEMA_VERSION,
    CandidateKnowledgeDocument,
)
from src.domain.models import CandidateProfile
from src.knowledge.hashing import (
    canonical_json,
    content_hash,
    profile_content_version,
    stable_id,
)


NATURAL_IDENTITY_FIELDS = {
    "experience": ("company", "role", "period"),
    "project": ("name", "organization", "year"),
    "education": ("course", "institution", "period"),
}


class CandidateKnowledgeDocumentBuilder:
    """Build traceable knowledge documents from existing profile content."""

    def build(
        self,
        profile: CandidateProfile,
    ) -> list[CandidateKnowledgeDocument]:
        profile_version = profile_content_version(profile)
        documents = []

        documents.extend(
            self._build_records(
                profile=profile,
                records=profile.experiences,
                source_type="experience",
                profile_version=profile_version,
            )
        )
        documents.extend(
            self._build_records(
                profile=profile,
                records=profile.projects,
                source_type="project",
                profile_version=profile_version,
            )
        )
        documents.extend(
            self._build_records(
                profile=profile,
                records=profile.educations,
                source_type="education",
                profile_version=profile_version,
            )
        )

        if profile.skills:
            documents.append(
                self._build_document(
                    candidate_id=profile.id,
                    source_type="skills",
                    source_ref="profile-skills",
                    content=f"skills: {canonical_json(profile.skills)}",
                    profile_version=profile_version,
                )
            )

        return documents

    def _build_records(
        self,
        profile: CandidateProfile,
        records: list[dict[str, Any]],
        source_type: str,
        profile_version: str,
    ) -> list[CandidateKnowledgeDocument]:
        documents = []

        for record in records:
            content = self._render_record(record)

            if not content:
                continue

            documents.append(
                self._build_document(
                    candidate_id=profile.id,
                    source_type=source_type,
                    source_ref=self._source_ref(source_type, record),
                    content=content,
                    profile_version=profile_version,
                )
            )

        return documents

    @staticmethod
    def _source_ref(source_type: str, record: dict[str, Any]) -> str:
        identity_fields = NATURAL_IDENTITY_FIELDS[source_type]
        identity = {
            field: record.get(field)
            for field in identity_fields
        }

        if all(
            value is not None and value != ""
            for value in identity.values()
        ):
            identity_payload = {
                "source_type": source_type,
                "identity": identity,
            }
        else:
            identity_payload = {
                "source_type": source_type,
                "record": record,
            }

        return f"{source_type}:{stable_id(identity_payload)}"

    @staticmethod
    def _render_record(record: dict[str, Any]) -> str:
        blocks = []

        for field in sorted(record):
            value = record[field]

            if value is None or value == "" or value == [] or value == {}:
                continue

            rendered = (
                value
                if isinstance(value, str)
                else json.dumps(
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            blocks.append(f"{field}: {rendered}")

        return "\n\n".join(blocks)

    @staticmethod
    def _build_document(
        candidate_id: str,
        source_type: str,
        source_ref: str,
        content: str,
        profile_version: str,
    ) -> CandidateKnowledgeDocument:
        source_hash = content_hash(content)

        return CandidateKnowledgeDocument(
            id=stable_id(
                {
                    "candidate_id": candidate_id,
                    "source_type": source_type,
                    "source_ref": source_ref,
                }
            ),
            candidate_id=candidate_id,
            source_type=source_type,
            source_ref=source_ref,
            content=content,
            metadata={
                "source_type": source_type,
                "source_ref": source_ref,
            },
            source_hash=source_hash,
            profile_version=profile_version,
            document_schema_version=DOCUMENT_SCHEMA_VERSION,
        )
