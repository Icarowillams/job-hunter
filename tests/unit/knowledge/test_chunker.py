from src.domain.candidate_knowledge import CandidateKnowledgeDocument
from src.knowledge.chunker import CHUNKING_VERSION, KnowledgeChunker
from src.knowledge.hashing import content_hash


def document(content):
    return CandidateKnowledgeDocument(
        id="document-1",
        candidate_id="candidate-1",
        source_type="experience",
        source_ref="experience:reference",
        content=content,
        metadata={"origin": "profile"},
        source_hash=content_hash(content),
        profile_version="profile-v1",
    )


def test_chunking_is_deterministic():
    knowledge_document = document("First paragraph.\n\nSecond paragraph.")
    chunker = KnowledgeChunker(max_chunk_chars=20)

    assert chunker.chunk(knowledge_document) == chunker.chunk(knowledge_document)


def test_chunks_preserve_document_id_and_metadata():
    chunk = KnowledgeChunker().chunk(document("Short document."))[0]

    assert chunk.document_id == "document-1"
    assert chunk.metadata["origin"] == "profile"
    assert chunk.metadata["source_type"] == "experience"
    assert chunk.metadata["source_ref"] == "experience:reference"
    assert chunk.metadata["chunking_version"] == CHUNKING_VERSION


def test_chunk_positions_are_deterministic():
    chunks = KnowledgeChunker(max_chunk_chars=20).chunk(
        document("First paragraph.\n\nSecond paragraph.")
    )

    assert [chunk.position for chunk in chunks] == [0, 1]


def test_small_document_generates_one_chunk():
    chunks = KnowledgeChunker().chunk(document("Short document."))

    assert len(chunks) == 1
    assert chunks[0].text == "Short document."


def test_large_document_can_generate_multiple_chunks():
    chunks = KnowledgeChunker(max_chunk_chars=25).chunk(
        document(
            "First paragraph has enough text.\n\n"
            "Second paragraph also has enough text."
        )
    )

    assert len(chunks) > 1
    assert all(chunk.content_hash == content_hash(chunk.text) for chunk in chunks)
