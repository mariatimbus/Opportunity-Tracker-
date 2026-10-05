# Architecture

Monorepo for the Student Opportunity Intelligence Platform. The frontend, backend, AI
services, and ingestion services live in one repository so types, tooling, and releases
stay in sync.

## Structure

- `apps/` — deployable applications
  - `apps/web` — Next.js frontend (placeholder)
  - `apps/api` — FastAPI backend (`opportunity_api` package, src layout)
- `services/` — background/standalone services
  - `services/ai` — Ollama adapters (embeddings, matching)
  - `services/ingestion` — opportunity scrapers/collectors
- `packages/` — shared libraries (`shared-types`, `config`)
- `database/` — Alembic migrations (`migrations/`) and seeds (`seeds/`)
- `tests/` — cross-app tests: `e2e/`, `fixtures/`
- `docs/` — this documentation, including `decisions/` (ADRs)
- `.github/` — CI workflows, issue templates, PR template

## Conventions

- Python backend: Python 3.13, managed with `uv`, linted with `ruff` (config in the repo
  root `pyproject.toml`), SQLAlchemy 2.0 typed models, Alembic for migrations.
- Frontend: Next.js (TBD in a later milestone).
- Database: PostgreSQL 16 via docker-compose for local dev; SQLite allowed for tests.
