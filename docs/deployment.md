# Deployment

The repository is configured for Render backend deployment and Vercel frontend deployment.

## Backend On Render

- Config file: `render.yaml`
- Root directory: `backend`
- Build command: `pip install --upgrade pip && pip install -r requirements.txt`
- Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`
- Health check path: `/health/ready`
- Persistent disk mount: `/opt/render/project/src/backend/data`

Required production environment:

```text
ALA_ENVIRONMENT=production
ALA_DEBUG=false
ALA_DATABASE_URL=sqlite+aiosqlite:////opt/render/project/src/backend/data/learning_assistant.db
ALA_GEMINI_API_KEY=<secret>
ALA_LLM_MODEL=gemini-2.5-flash
ALA_EMBEDDING_MODEL=gemini-embedding-2
ALA_EMBEDDING_DIMENSIONS=768
ALA_CHROMA_PATH=/opt/render/project/src/backend/data/chroma
ALA_AI_CACHE_PATH=/opt/render/project/src/backend/data/ai-cache.sqlite3
ALA_AI_METRICS_PATH=/opt/render/project/src/backend/data/ai-metrics.jsonl
ALA_CORS_ALLOWED_ORIGINS=["https://adaptive-learning-ai.vercel.app"]
ALA_TRUSTED_HOSTS=["adaptive-learning-ai-api.onrender.com"]
ALA_ALLOW_ANONYMOUS_LEARNER=false
```

SQLite and local ChromaDB require a single Render API instance with persistent disk.

## Frontend On Vercel

- Config file: `frontend/vercel.json`
- Root directory: `frontend`
- Install command: `npm ci`
- Build command: `npm run build`
- Public API URL: `NEXT_PUBLIC_API_URL=https://adaptive-learning-ai-api.onrender.com`
- Public app version: `NEXT_PUBLIC_APP_VERSION=0.1.0`

If the Render service URL changes, update `NEXT_PUBLIC_API_URL` in Vercel and in
`frontend/vercel.json`.

## Docker

`backend/Dockerfile` installs runtime dependencies, copies the app and Alembic files, runs migrations,
and starts Uvicorn as a non-root user.

## Health Checks

- `/health/live` confirms process liveness.
- `/health/ready` verifies database connectivity and is used by Render.
