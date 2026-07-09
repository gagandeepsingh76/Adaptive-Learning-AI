# Architecture

Adaptive Learning AI is a full-stack learning application with a Next.js frontend and a FastAPI
backend.

## Components

- **Frontend:** Next.js App Router pages for Home, Roadmap, Project, Chat, Progress, Settings, and
  Not Found. A shared Axios client handles API calls, retries, learner identity headers, and friendly
  errors.
- **Backend:** FastAPI routes, service classes, repository/unit-of-work persistence, SQLModel models,
  Alembic migrations, structured logging, payload limits, CORS, and trusted-host middleware.
- **AI Platform:** Gemini structured generation, prompt management, JSON validation, repair,
  quality evaluation, embeddings, ChromaDB retrieval, context building, cache, and metrics sink.
- **Persistence:** SQLite is the source of record; ChromaDB is a rebuildable vector projection.

## Request Flow

```mermaid
flowchart LR
  Browser[Next.js Browser App] --> Client[Typed API Client]
  Client --> API[FastAPI Routes]
  API --> Services[Service Layer]
  Services --> UOW[Unit Of Work]
  UOW --> SQL[(SQLite)]
  Services --> AI[AI Platform]
  AI --> Gemini[Gemini]
  AI --> Chroma[(ChromaDB)]
```

## RAG Flow

```mermaid
flowchart LR
  Roadmap[Roadmap Hierarchy] --> Docs[Semantic Documents]
  Docs --> Chunks[Chunks With Metadata]
  Chunks --> Embeddings[gemini-embedding-2]
  Embeddings --> Chroma[(ChromaDB)]
  Question[Question] --> Query[Query Embedding]
  Query --> Retrieve[Scoped Retrieval]
  Chroma --> Retrieve
  Retrieve --> Context[Bounded Context]
  Context --> Prompt[Chat Prompt]
  Prompt --> Answer[Structured Answer With Citations]
```

The chat prompt receives retrieved chunks only, not the entire roadmap.
