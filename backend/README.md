# AI Learning Assistant Backend

FastAPI backend for personalized roadmap generation, project recommendations, retrieval-augmented
chat, and learning progress tracking.

## Local development

1. Install Python 3.12 and create a virtual environment.
2. Install `pip install -e ".[dev]"`.
3. Copy `.env.example` to `.env` and provide `ALA_GEMINI_API_KEY` for AI endpoints.
4. Run migrations with `alembic upgrade head`.
5. Start the API with `uvicorn app.main:app --reload`.
6. Run verification with `ruff check .`, `mypy app`, `pytest`, and `alembic upgrade head`.

SQLite and ChromaDB data are stored under the configured persistent data directory. Production
deployments using SQLite must run a single API instance; the repository boundary supports a later
PostgreSQL migration.
