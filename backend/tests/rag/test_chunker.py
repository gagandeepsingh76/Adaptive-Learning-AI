"""Semantic chunking and document decomposition tests."""

import json
from uuid import uuid4

from app.ai.validation import ResponseValidator
from app.rag.chunker import SemanticChunker
from app.rag.documents import RoadmapDocumentFactory
from app.schemas.ai_outputs import GeneratedRoadmap
from tests.unit.test_validation import valid_roadmap


def test_document_factory_preserves_hierarchy_and_chunk_ids_are_stable() -> None:
    roadmap = ResponseValidator(GeneratedRoadmap).validate_json(json.dumps(valid_roadmap()))
    documents = RoadmapDocumentFactory().create(
        roadmap,
        roadmap_id=uuid4(),
        learner_id=uuid4(),
        content_version=1,
        embedding_version="gemini-embedding-2:d3",
        prompt_version="1.0.0",
    )
    chunker = SemanticChunker(100, 150, 20)

    first = tuple(chunk for document in documents for chunk in chunker.chunk(document))
    second = tuple(chunk for document in documents for chunk in chunker.chunk(document))

    assert len(documents) == 3
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert all(chunk.metadata["roadmap_id"] for chunk in first)
    assert any(chunk.parent_id is not None for chunk in first)

