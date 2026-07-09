"""Retrieval-augmented chat business workflow."""

from collections.abc import Callable
from uuid import UUID

from app.ai.structured import StructuredGenerationEngine
from app.core.enums import IndexStatus, MessageRole, ProcessingStatus
from app.core.interfaces.ai import GenerationRequest, PromptRenderer
from app.core.interfaces.repositories import UnitOfWork
from app.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models import Conversation, Message
from app.rag.context import ContextBuilder
from app.rag.retriever import RetrievalRequest, Retriever
from app.schemas.ai_outputs import ChatAnswer, FollowUpQuestions
from app.schemas.chat import ChatRequest, ChatResponse, CitationResponse


class ChatService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        prompts: PromptRenderer,
        generator: StructuredGenerationEngine,
        retriever: Retriever,
        context_builder: ContextBuilder,
    ) -> None:
        self._uow_factory = uow_factory
        self._prompts = prompts
        self._generator = generator
        self._retriever = retriever
        self._context_builder = context_builder

    async def chat(
        self, learner_id: UUID, command: ChatRequest, request_id: str | None = None
    ) -> ChatResponse:
        async with self._uow_factory() as uow:
            roadmap = await uow.roadmaps.get(command.roadmap_id, learner_id)
            if roadmap is None:
                raise ResourceNotFoundError("Roadmap was not found.")
            if roadmap.index_status is not IndexStatus.READY:
                raise ResourceConflictError("Roadmap retrieval index is not ready.")
            conversation = (
                await uow.conversations.get_conversation(
                    command.conversation_id, learner_id, command.roadmap_id
                )
                if command.conversation_id
                else None
            )
            if conversation is None:
                conversation = await uow.conversations.add_conversation(
                    Conversation(learner_id=learner_id, roadmap_id=roadmap.id)
                )
            history = await uow.conversations.recent_messages(conversation.id, 8)
            user_message = Message(
                conversation_id=conversation.id,
                sequence_number=conversation.next_sequence,
                role=MessageRole.USER,
                content=command.question,
                processing_status=ProcessingStatus.PENDING,
            )
            conversation.next_sequence += 1
            await uow.conversations.add_message(user_message)
            await uow.commit()

        retrieved = await self._retriever.retrieve(
            RetrievalRequest(
                command.question,
                str(learner_id),
                str(command.roadmap_id),
                roadmap.indexed_content_version or roadmap.content_version,
                request_id=request_id,
            )
        )
        context = self._context_builder.build(retrieved)
        rendered = await self._prompts.render(
            "chat",
            {
                "question": command.question,
                "conversation_context": [
                    {"role": item.role.value, "content": item.content} for item in history
                ],
                "retrieved_context": context.text,
            },
        )
        answer = await self._generator.generate(
            GenerationRequest(
                prompt=rendered.text,
                prompt_id=rendered.prompt_id,
                prompt_version=rendered.version,
                request_id=request_id,
                roadmap_id=str(command.roadmap_id),
            ),
            ChatAnswer,
            validate_quality=False,
        )
        citations = [source for source in context.sources if source.source_id in answer.source_ids]
        follow_up = await self._follow_up(command.question, answer, context.text, request_id)
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_conversation(
                conversation.id, learner_id, command.roadmap_id
            )
            if conversation is None:
                raise ResourceNotFoundError("Conversation was not found.")
            persisted_user = await uow.conversations.get_message(user_message.id)
            if persisted_user is not None:
                persisted_user.processing_status = ProcessingStatus.PROCESSED
            assistant = Message(
                conversation_id=conversation.id,
                sequence_number=conversation.next_sequence,
                role=MessageRole.ASSISTANT,
                content=answer.answer,
                processing_status=ProcessingStatus.PROCESSED,
                source_citations=[{"source_id": item.source_id} for item in citations],
            )
            conversation.next_sequence += 1
            await uow.conversations.add_message(assistant)
            await uow.commit()
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant.id,
            answer=answer.answer,
            citations=[
                CitationResponse(
                    source_id=source.source_id,
                    entity_type=source.entity_type,
                    entity_id=source.entity_id,
                    relevance=source.relevance,
                )
                for source in citations
            ],
            follow_up_questions=follow_up.questions,
        )

    async def _follow_up(
        self, question: str, answer: ChatAnswer, context: str, request_id: str | None
    ) -> FollowUpQuestions:
        rendered = await self._prompts.render(
            "follow_up",
            {"question": question, "answer": answer.answer, "source_summaries": context},
        )
        return await self._generator.generate(
            GenerationRequest(
                prompt=rendered.text,
                prompt_id=rendered.prompt_id,
                prompt_version=rendered.version,
                request_id=request_id,
            ),
            FollowUpQuestions,
            validate_quality=False,
        )
