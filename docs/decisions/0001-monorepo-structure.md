# ADR 0001: Monorepo with apps/services/packages

## Status

Accepted

## Context

The platform spans a Next.js frontend, a FastAPI backend, Ollama-based AI services, and
ingestion workers. Sharing types and contracts between these, plus coordinating releases,
is painful across multiple repositories at this team size.

## Decision

Use a single monorepo with three top-level buckets:

- `apps/` — user-facing deployables (web, api)
- `services/` — independently runnable backend services (ai, ingestion)
- `packages/` — shared libraries (types, config)

`database/` holds migrations and seeds; `tests/` holds cross-app suites.

## Consequences

- One PR can change an API and its consumer atomically; CI runs once per PR.
- Repo tooling (ruff config, CI, templates) lives at the root and is shared.
- The repo can grow large; we mitigate by keeping each directory self-contained with
  its own manifest, so extraction later remains possible.
