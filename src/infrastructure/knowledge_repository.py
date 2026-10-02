import json
from dataclasses import dataclass

from src.domain.candidate_knowledge import (
    CandidateKnowledgeDocument,
    KnowledgeChunk,
)
from src.infrastructure.database import Database


@dataclass
class KnowledgeSyncResult:
    """Summary of one incremental knowledge synchronization."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0


class KnowledgeRepository:
    def __init__(self, database: Database):
        self.database = database

    def sync(
        self,
        candidate_id: str,
        documents: list[CandidateKnowledgeDocument],
        chunks: list[KnowledgeChunk],
    ) -> KnowledgeSyncResult:
        """Reconcile stored knowledge with one deterministic rebuild.

        Documents are compared by source_hash, profile_version and
        document_schema_version. Only rows that changed are rewritten,
        chunks are replaced only for documents whose content or chunk
        set changed, and stored documents missing from the rebuild are
        removed. The whole reconciliation runs in a single transaction.
        """
        chunks_by_document: dict[str, list[KnowledgeChunk]] = {}
        for chunk in chunks:
            chunks_by_document.setdefault(chunk.document_id, []).append(chunk)

        incoming_ids = {document.id for document in documents}
        result = KnowledgeSyncResult()

        with self.database.connect() as conn:
            stored_state = {
                row[0]: (row[1], row[2], row[3])
                for row in conn.execute(
                    """
                    SELECT
                        id,
                        source_hash,
                        profile_version,
                        document_schema_version
                    FROM knowledge_document
                    WHERE candidate_id = ?
                    """,
                    (candidate_id,),
                ).fetchall()
            }

            stored_chunks: dict[str, dict[str, dict]] = {}
            for row in conn.execute(
                """
                SELECT
                    knowledge_chunk.id,
                    knowledge_chunk.document_id,
                    knowledge_chunk.metadata
                FROM knowledge_chunk
                INNER JOIN knowledge_document
                    ON knowledge_document.id = knowledge_chunk.document_id
                WHERE knowledge_document.candidate_id = ?
                """,
                (candidate_id,),
            ).fetchall():
                stored_chunks.setdefault(row[1], {})[row[0]] = (
                    json.loads(row[2]) if row[2] else {}
                )

            for document in documents:
                incoming_chunks = {
                    chunk.id: chunk.metadata
                    for chunk in chunks_by_document.get(document.id, [])
                }
                state = (
                    document.source_hash,
                    document.profile_version,
                    document.document_schema_version,
                )
                stored = stored_state.get(document.id)
                chunks_changed = (
                    stored_chunks.get(document.id, {})
                    != incoming_chunks
                )

                if stored is None:
                    self._insert_document(conn, document)
                    result.created += 1
                elif stored != state:
                    self._update_document(conn, document)
                    result.updated += 1
                elif chunks_changed:
                    result.updated += 1
                else:
                    result.unchanged += 1
                    continue

                if chunks_changed:
                    conn.execute(
                        """
                        DELETE FROM knowledge_chunk
                        WHERE document_id = ?
                        """,
                        (document.id,),
                    )
                    for chunk in chunks_by_document.get(document.id, []):
                        self._insert_chunk(conn, chunk)

            for stale_id in set(stored_state) - incoming_ids:
                conn.execute(
                    """
                    DELETE FROM knowledge_document
                    WHERE id = ?
                    """,
                    (stale_id,),
                )
                result.removed += 1

        return result

    def list_documents(
        self,
        candidate_id: str,
    ) -> list[CandidateKnowledgeDocument]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    candidate_id,
                    source_type,
                    source_ref,
                    content,
                    metadata,
                    source_hash,
                    profile_version,
                    document_schema_version
                FROM knowledge_document
                WHERE candidate_id = ?
                ORDER BY source_type, source_ref
                """,
                (candidate_id,),
            ).fetchall()

        return [self._row_to_document(row) for row in rows]

    def list_chunks(
        self,
        document_id: str,
    ) -> list[KnowledgeChunk]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    document_id,
                    position,
                    text,
                    content_hash,
                    metadata
                FROM knowledge_chunk
                WHERE document_id = ?
                ORDER BY position
                """,
                (document_id,),
            ).fetchall()

        return [self._row_to_chunk(row) for row in rows]

    @staticmethod
    def _insert_document(
        conn,
        document: CandidateKnowledgeDocument,
    ) -> None:
        conn.execute(
            """
            INSERT INTO knowledge_document (
                id,
                candidate_id,
                source_type,
                source_ref,
                content,
                metadata,
                source_hash,
                profile_version,
                document_schema_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.id,
                document.candidate_id,
                document.source_type,
                document.source_ref,
                document.content,
                json.dumps(document.metadata),
                document.source_hash,
                document.profile_version,
                document.document_schema_version,
            ),
        )

    @staticmethod
    def _update_document(
        conn,
        document: CandidateKnowledgeDocument,
    ) -> None:
        conn.execute(
            """
            UPDATE knowledge_document
            SET
                source_type = ?,
                source_ref = ?,
                content = ?,
                metadata = ?,
                source_hash = ?,
                profile_version = ?,
                document_schema_version = ?
            WHERE id = ?
            """,
            (
                document.source_type,
                document.source_ref,
                document.content,
                json.dumps(document.metadata),
                document.source_hash,
                document.profile_version,
                document.document_schema_version,
                document.id,
            ),
        )

    @staticmethod
    def _insert_chunk(conn, chunk: KnowledgeChunk) -> None:
        conn.execute(
            """
            INSERT INTO knowledge_chunk (
                id,
                document_id,
                position,
                text,
                content_hash,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.id,
                chunk.document_id,
                chunk.position,
                chunk.text,
                chunk.content_hash,
                json.dumps(chunk.metadata),
            ),
        )

    @staticmethod
    def _row_to_document(row) -> CandidateKnowledgeDocument:
        return CandidateKnowledgeDocument(
            id=row[0],
            candidate_id=row[1],
            source_type=row[2],
            source_ref=row[3],
            content=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            source_hash=row[6],
            profile_version=row[7],
            document_schema_version=row[8],
        )

    @staticmethod
    def _row_to_chunk(row) -> KnowledgeChunk:
        return KnowledgeChunk(
            id=row[0],
            document_id=row[1],
            position=row[2],
            text=row[3],
            content_hash=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
        )
