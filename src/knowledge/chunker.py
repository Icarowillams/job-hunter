import re

from src.domain.candidate_knowledge import KnowledgeChunk
from src.knowledge.hashing import content_hash, stable_id


CHUNKING_VERSION = "v1"


class KnowledgeChunker:
    """Split documents deterministically while preserving paragraph boundaries."""

    def __init__(self, max_chunk_chars: int = 500):
        if max_chunk_chars <= 0:
            raise ValueError("max_chunk_chars must be greater than zero")

        self.max_chunk_chars = max_chunk_chars

    def chunk(self, document) -> list[KnowledgeChunk]:
        texts = self._split(document.content)

        return [
            KnowledgeChunk(
                id=stable_id(
                    {
                        "document_id": document.id,
                        "position": position,
                        "content_hash": content_hash(text),
                    }
                ),
                document_id=document.id,
                position=position,
                text=text,
                content_hash=content_hash(text),
                metadata={
                    **document.metadata,
                    "source_type": document.source_type,
                    "source_ref": document.source_ref,
                    "document_schema_version": document.document_schema_version,
                    "chunking_version": CHUNKING_VERSION,
                },
            )
            for position, text in enumerate(texts)
        ]

    def _split(self, content: str) -> list[str]:
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", content)
            if paragraph.strip()
        ]

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            for piece in self._split_long_paragraph(paragraph):
                separator = "\n\n" if current else ""

                if (
                    current
                    and len(current) + len(separator) + len(piece)
                    > self.max_chunk_chars
                ):
                    chunks.append(current)
                    current = piece
                else:
                    current = f"{current}{separator}{piece}"

        if current:
            chunks.append(current)

        return chunks

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        if len(paragraph) <= self.max_chunk_chars:
            return [paragraph]

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        pieces: list[str] = []
        current = ""

        for sentence in sentences:
            for part in self._split_long_text(sentence):
                separator = " " if current else ""

                if (
                    current
                    and len(current) + len(separator) + len(part)
                    > self.max_chunk_chars
                ):
                    pieces.append(current)
                    current = part
                else:
                    current = f"{current}{separator}{part}"

        if current:
            pieces.append(current)

        return pieces

    def _split_long_text(self, text: str) -> list[str]:
        if len(text) <= self.max_chunk_chars:
            return [text]

        words = text.split()
        pieces: list[str] = []
        current = ""

        for word in words:
            separator = " " if current else ""

            if (
                current
                and len(current) + len(separator) + len(word)
                > self.max_chunk_chars
            ):
                pieces.append(current)
                current = word
            else:
                current = f"{current}{separator}{word}"

        if current:
            pieces.append(current)

        return pieces
