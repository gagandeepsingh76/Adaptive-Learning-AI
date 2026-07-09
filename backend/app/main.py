"""FastAPI application bootstrap."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.ai.platform import AIPlatform, build_ai_platform
from app.api.dependencies import ServiceContainer
from app.api.error_handlers import register_exception_handlers
from app.api.routes.business import router as business_router
from app.api.routes.health import router as health_router
from app.config.ai_settings import AISettings
from app.config.logging import configure_logging, get_logger
from app.config.settings import Environment, Settings, get_settings
from app.database.engine import create_database
from app.database.initialization import verify_database
from app.middleware.payload_limit import PayloadLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.rag.documents import RoadmapDocumentFactory
from app.repositories.sql import unit_of_work_factory
from app.services.chat_service import ChatService
from app.services.progress_service import ProgressService
from app.services.project_service import ProjectService
from app.services.resource_service import LearningResourceService
from app.services.roadmap_service import RoadmapService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct an application with explicit, testable dependencies."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = create_database(resolved_settings)
        ai_platform: AIPlatform | None = None
        application.state.settings = resolved_settings
        application.state.database = database
        if resolved_settings.environment is Environment.TEST:
            await database.create_schema_for_tests()
        await verify_database(database)
        uow = unit_of_work_factory(database.session_factory)
        application.state.services = ServiceContainer(
            roadmaps=None,
            projects=None,
            chat=None,
            progress=ProgressService(uow),
            resources=LearningResourceService(uow),
        )
        if resolved_settings.gemini_api_key is not None:
            ai_settings = AISettings.from_settings(resolved_settings)
            ai_platform = build_ai_platform(
                api_key=resolved_settings.gemini_api_key.get_secret_value(),
                settings=ai_settings,
                prompt_root=resolved_settings.prompt_root,
                chroma_path=resolved_settings.chroma_path,
                collection_name=resolved_settings.chroma_collection_name,
                chunk_target_tokens=resolved_settings.chunk_target_tokens,
                chunk_max_tokens=resolved_settings.chunk_max_tokens,
                chunk_overlap_tokens=resolved_settings.chunk_overlap_tokens,
            )
            await ai_platform.initialize()
            application.state.ai_platform = ai_platform
            application.state.services = ServiceContainer(
                roadmaps=RoadmapService(
                    uow,
                    ai_platform.prompts,
                    ai_platform.generator,
                    RoadmapDocumentFactory(),
                    ai_platform.indexer,
                    f"{resolved_settings.embedding_model}:d{resolved_settings.embedding_dimensions}",
                ),
                projects=ProjectService(uow, ai_platform.prompts, ai_platform.generator),
                chat=ChatService(
                    uow,
                    ai_platform.prompts,
                    ai_platform.generator,
                    ai_platform.retriever,
                    ai_platform.context_builder,
                ),
                progress=ProgressService(uow),
                resources=LearningResourceService(uow),
            )
        else:
            logger.warning(
                "ai.provider.unconfigured",
                provider="gemini",
                missing_env="ALA_GEMINI_API_KEY",
            )
        logger.info(
            "application.started",
            environment=resolved_settings.environment.value,
            version=resolved_settings.app_version,
        )
        try:
            yield
        finally:
            if ai_platform is not None:
                await ai_platform.close()
            await database.dispose()
            logger.info("application.stopped")

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allowed_origins,
        allow_origin_regex=resolved_settings.cors_allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Learner-ID", "X-Request-ID"],
    )
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=resolved_settings.trusted_hosts
    )
    application.add_middleware(
        PayloadLimitMiddleware, max_bytes=resolved_settings.max_request_bytes
    )
    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(business_router)
    return application


app = create_app()
