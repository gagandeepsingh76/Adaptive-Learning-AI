# Demo Walkthrough

## 3-5 Minute Demo Script

### 0:00-0:30 - Product framing

"Adaptive Learning AI is a full-stack learning SaaS product. It turns a learner goal into a
structured roadmap, recommends a portfolio project, answers roadmap-grounded questions with RAG
citations, and tracks progress. The frontend is Next.js, the backend is FastAPI, and the AI layer
uses Gemini plus ChromaDB."

Show the homepage and point to the roadmap, RAG, project, and progress signals in the hero.

### 0:30-1:30 - Roadmap generation

"I start with a goal, existing skills, weekly hours, learning style, and constraints. The backend
validates the request, generates structured JSON, persists the hierarchy, and indexes it for
retrieval."

Open Roadmap, submit the form, then expand a skill. Call out estimated hours, estimated weeks,
learning timeline, skills, tasks, subtasks, completion criteria, and progress badges.

### 1:30-2:15 - Project recommendation

"The project generator supports two assignment modes. I can generate from the roadmap ID or provide
a direct goal plus skills. The backend enforces that only one mode is used."

Open Project, generate from the roadmap, and point to difficulty, estimated hours, tech stack,
requirements, deliverables, acceptance criteria, rationale, and recommended learning resources.

### 2:15-3:05 - RAG chat

"The chat experience is intentionally transparent: it says answers come from retrieval, keeps
conversation history, shows a typing state, and displays citation cards for retrieved context."

Open Chat, ask a question about sequencing or portfolio priorities, then show the retrieved context
indicator, citations, and follow-up questions.

### 3:05-3:40 - Progress tracking

"Progress is tied to the roadmap hierarchy. Completing subtasks updates the backend and the progress
page summarizes completion, completed skills, pending skills, completed tasks, learning statistics,
and estimated time remaining."

Open Progress after marking a subtask complete on Roadmap.

### 3:40-4:30 - Production readiness

"The Settings page shows backend URL configuration, model metadata, app version, and live health
checks. Deployment is configured for Vercel and Render, and CI runs Ruff, MyPy, Pytest, Alembic,
backend build, frontend lint, frontend type-check, frontend tests, and frontend build."

Open Settings, run health, and show `render.yaml`, `frontend/vercel.json`, and `.github/workflows/ci.yml`.

## Talking Points

- The frontend uses typed contracts that mirror backend Pydantic schemas.
- API errors are centralized and turned into friendly recovery messages.
- The learner identity is stored locally and sent as `X-Learner-ID`.
- Production backend configuration rejects wildcard CORS and anonymous learners.
- Render uses a persistent disk for SQLite, ChromaDB, AI metrics, and response cache.
- The UI favors dense, scannable SaaS workflows instead of flashy presentation.

## Architecture Explanation

The frontend is a Next.js App Router application. Each page owns its form state and calls a shared
Axios client. The client adds the learner header, applies timeouts, retries transient backend errors,
and raises friendly `ApiClientError` messages.

The backend is layered. FastAPI routes stay thin, services coordinate business workflows, repositories
own persistence, and the AI platform owns prompts, generation, embeddings, retrieval, repair, cache,
evaluation, and observability. Roadmap generation creates both relational records and vector-searchable
documents. Chat retrieves roadmap-scoped context before prompting Gemini.

## Interview Explanation

This project demonstrates end-to-end engineering judgment:

- Product thinking: the user flow moves from planning to building to support to progress.
- Backend design: strict settings, typed schemas, layered services, repository boundaries, and tests.
- AI reliability: structured generation, validation, repair, prompt versioning, caching, and citations.
- Frontend quality: accessible forms, loading states, empty states, error recovery, responsive layout,
  and typed integration.
- Deployment readiness: health checks, CORS configuration, persistent storage, Vercel/Render config,
  and CI that fails on quality regressions.
