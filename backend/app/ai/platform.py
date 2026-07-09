"""Framework-independent AI platform composition root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ai.cache import SQLiteAICache
from app.ai.embeddings import GeminiEmbeddingProvider
from app.ai.evaluation import GenerationEvaluator
from app.ai.gemini import GeminiProvider
from app.ai.observability import JsonlAIObservabilitySink
from app.ai.repair import PromptRepairEngine
from app.ai.structured import StructuredGenerationEngine
from app.config.ai_settings import AISettings
from app.prompts.manager import PromptManager
from app.rag.chroma import ChromaCollectionManager, ChromaVectorStore
from app.rag.chunker import SemanticChunker
from app.rag.context import ContextBuilder
from app.rag.indexer import RAGIndexer
from app.rag.retriever import Retriever


@dataclass(slots=True)
class AIPlatform:
    """Ready-to-consume AI capabilities with explicit lifecycle ownership."""

    generator: StructuredGenerationEngine
    prompts: PromptManager
    embeddings: GeminiEmbeddingProvider
    indexer: RAGIndexer
    retriever: Retriever
    context_builder: ContextBuilder
    vector_store: ChromaVectorStore
    cache: SQLiteAICache
    observability: JsonlAIObservabilitySink

    async def initialize(self) -> None:
        """Initialize persistent vector infrastructure."""
        await self.vector_store.initialize()

    async def close(self) -> None:
        """Release persistent resources owned by the platform."""
        await self.vector_store.close()
        await self.cache.close()
        await self.observability.close()


def build_ai_platform(
    *,
    api_key: str,
    settings: AISettings,
    prompt_root: Path,
    chroma_path: Path,
    collection_name: str,
    chunk_target_tokens: int = 400,
    chunk_max_tokens: int = 600,
    chunk_overlap_tokens: int = 60,
    retrieval_cache_ttl_seconds: int = 300,
) -> AIPlatform:
    """Compose AI adapters without importing FastAPI or application services."""
    cache = SQLiteAICache(settings.cache_path)
    observability = JsonlAIObservabilitySink(settings.metrics_path)
    prompts = PromptManager(prompt_root, cache)
    llm = GeminiProvider(api_key, settings, observability)
    embeddings = GeminiEmbeddingProvider(api_key, settings, cache, observability)
    evaluator = GenerationEvaluator(
        settings.quality_threshold,
        cache,
        provider=llm,
        prompt_renderer=prompts,
    )
    repair = PromptRepairEngine(llm, prompts)
    generator = StructuredGenerationEngine(
        llm, repair, evaluator, cache, observability
    )
    manager = ChromaCollectionManager(
        chroma_path, collection_name, settings.embedding_dimensions
    )
    vector_store = ChromaVectorStore(manager, settings.embedding_dimensions)
    chunker = SemanticChunker(
        chunk_target_tokens, chunk_max_tokens, chunk_overlap_tokens
    )
    indexer = RAGIndexer(chunker, embeddings, vector_store)
    retriever = Retriever(
        embeddings,
        vector_store,
        cache,
        cache_ttl_seconds=retrieval_cache_ttl_seconds,
    )
    return AIPlatform(
        generator=generator,
        prompts=prompts,
        embeddings=embeddings,
        indexer=indexer,
        retriever=retriever,
        context_builder=ContextBuilder(),
        vector_store=vector_store,
        cache=cache,
        observability=observability,
    )
