# Backend Design

This document describes the implemented FastAPI backend for Adaptive Learning AI.

## Runtime Stack

- Python 3.12
- FastAPI and Uvicorn
- SQLModel, SQLAlchemy, Alembic, and SQLite
- ChromaDB for vector storage
- Gemini 2.5 Flash for structured generation
- `gemini-embedding-2` with 768 dimensions for retrieval embeddings
- Jinja2 prompt templates with manifest metadata
- Ruff, MyPy, Pytest, and Alembic for release verification

## Architecture

The backend is layered around explicit dependency boundaries:

- API routes translate HTTP requests into typed service calls.
- Services orchestrate roadmap, project, chat, progress, and resource workflows.
- Repositories and a unit of work own SQL persistence and transaction boundaries.
- The AI platform owns prompt rendering, Gemini generation, repair, evaluation, embeddings,
  retrieval, caching, and observability.
- ChromaDB is a rebuildable retrieval projection; SQL remains the source of record.

Long-lived resources are composed once in FastAPI lifespan startup. Routes receive a service
container through FastAPI dependencies and do not instantiate provider clients directly.

## API Workflows

### `POST /roadmap`

The roadmap flow validates the request, renders the versioned roadmap prompt, asks Gemini for
structured JSON, validates and evaluates the result, persists the roadmap hierarchy, converts the
hierarchy into semantic documents, chunks the documents, embeds them, writes them to ChromaDB, and
marks the roadmap index as ready. If indexing fails, SQL state remains recoverable and chat refuses
to answer until the index is ready.

### `POST /project`

The project flow supports exactly one source mode per request: a generated roadmap ID, or a direct
goal plus skills. The service validates ownership in roadmap mode, renders the versioned project
prompt, validates structured JSON, persists the project and normalized skill snapshots, and returns
a typed response.

### `POST /chat`

The chat flow loads the learner-owned roadmap and conversation, requires `index_status=ready`, stores
the user turn, normalizes and embeds the question, retrieves only roadmap-scoped chunks from ChromaDB,
builds bounded context, renders the chat prompt, validates the structured answer, creates follow-up
questions, persists the assistant turn, and returns citations tied to retrieved source IDs.

The chat prompt never receives the complete roadmap object. It receives only selected retrieved
chunks under a context budget.

## Data Model

The SQLModel metadata includes:

- `roadmaps`
- `skills`
- `tasks`
- `subtasks`
- `projects`
- `project_skills`
- `conversations`
- `messages`
- `progress_records`
- `learning_resources`
- `prompt_versions`
- `response_cache`
- `embedding_cache`
- `generation_evaluations`

Roadmap child rows use cascade delete where they are part of the aggregate. Prompt-version foreign
keys use restricted deletion to preserve generation history. Projects can survive roadmap deletion
through nullable roadmap references.

Alembic owns schema creation and deployment migrations. `metadata.create_all()` is used only for
isolated test verification.

## RAG Implementation

The implemented RAG pipeline includes:

- Hierarchy-aware semantic chunking with inherited metadata.
- Gemini embedding generation through a provider abstraction.
- Model- and dimension-isolated Chroma collections.
- Mandatory learner, roadmap, and content-version filters.
- Query expansion and reciprocal-rank fusion.
- Top-K context selection with a token budget.
- Citation source IDs derived only from retrieved chunks.
- Conversation persistence across user and assistant turns.

## Prompt And JSON Safety

Prompts live under `app/prompts/templates`. Each prompt has a manifest and a versioned Jinja2 file.
User input and retrieved content are serialized as JSON inside delimited prompt regions and described
as untrusted data. Responses are parsed into strict Pydantic schemas. Invalid JSON enters a bounded
repair/regeneration path rather than being persisted as trusted state.

## Security Controls

- Production requires `ALA_GEMINI_API_KEY`.
- Production rejects anonymous learners.
- Production rejects wildcard CORS origins and trusted hosts.
- Request payload size is bounded by middleware.
- API errors use centralized non-sensitive error envelopes.
- Learner identity is taken from `X-Learner-ID` or the configured local anonymous learner policy,
  never from request bodies.
- SQL lookups and vector retrieval are learner-scoped.
- Secrets, prompts, questions, generated content, and vectors are not logged as raw values.

## Deployment Behavior

Render and Docker startup run `alembic upgrade head` before Uvicorn starts. Render uses a persistent
disk for SQLite, ChromaDB, AI cache, and AI metrics. SQLite deployment is intended for a single API
instance.

## Verification

The release gate for the backend is:

```bash
ruff check .
mypy app
pytest
alembic upgrade head
python -m build
```

Additional release smoke checks verify FastAPI startup, `/health`, `/health/ready`, OpenAPI
generation, SQLModel mappings, and `metadata.create_all()` against a temporary database.
