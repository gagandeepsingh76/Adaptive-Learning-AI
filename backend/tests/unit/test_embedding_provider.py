"""Gemini embedding adapter tests without network access."""

from types import SimpleNamespace

from app.ai.embeddings import GeminiEmbeddingProvider
from app.core.interfaces.ai import EmbeddingInput, EmbeddingPurpose, EmbeddingRequest


class FakeEmbeddingModels:
    def __init__(self) -> None:
        self.calls = 0
        self.contents: list[str] = []

    async def embed_content(self, *, model, contents, config):
        self.calls += 1
        self.contents.append(contents)
        assert model == "gemini-embedding-2"
        assert config.output_dimensionality == 3
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 0.0, 0.0])])


async def test_embedding_batch_preserves_metadata_and_uses_cache(ai_settings, ai_cache) -> None:
    models = FakeEmbeddingModels()
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiEmbeddingProvider("", ai_settings, ai_cache, client=client)
    request = EmbeddingRequest(
        items=(EmbeddingInput("HTTP", {"id": "a"}), EmbeddingInput("SQL", {"id": "b"})),
        purpose=EmbeddingPurpose.DOCUMENT,
    )

    first = await provider.embed(request)
    second = await provider.embed(request)

    assert [item.metadata["id"] for item in first.items] == ["a", "b"]
    assert models.calls == 2
    assert all(item.cached for item in second.items)
    assert all(content.startswith("Document:") for content in models.contents)

