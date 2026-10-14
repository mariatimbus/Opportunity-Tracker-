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

## Platform: Supabase-first

Supabase is the identity and data backbone; the FastAPI backend is a domain API
on top of it (decided in [ADR 0003](decisions/0003-supabase-first-architecture.md),
which supersedes ADR 0002's auth section).

- **Supabase Auth (GoTrue) is the only token issuer.** Clients sign up/in
  directly against Supabase; `apps/api` only validates Supabase-issued JWTs
  (signature + `iss`/`aud`) and mirrors identities into the local `users` table
  on first authenticated request. The backend never handles passwords.
- **Supabase Postgres hosts the domain schema.** SQLAlchemy/Alembic in
  `database/migrations/` remain the migration toolchain; migrations are applied
  to the Supabase database.
- The API stays the primary enforcement point for business rules; row-level
  security is an optional second line of defense for later.
- Backend auth config: `APP_SUPABASE_URL`, `APP_SUPABASE_JWT_SECRET`,
  `APP_SUPABASE_JWT_AUDIENCE` (see `.env.example`).

## Conventions

- Python backend: Python 3.13, managed with `uv`, linted with `ruff` (config in the repo
  root `pyproject.toml`), SQLAlchemy 2.0 typed models, Alembic for migrations.
- Frontend: Next.js (TBD in a later milestone).
- Database: Supabase-hosted Postgres 16 (cloud project or `supabase start` CLI)
  for dev; SQLite allowed for tests.
