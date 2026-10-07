# ADR 0002: API conventions and contract workflow

## Status

Proposed — pending sign-off from B (frontend) and C (data/ingestion).

## Context

The frontend (`apps/web`), the ingestion service (`services/ingestion`), and the
FastAPI backend are built in parallel by different people. Without a frozen contract,
field naming, path style, and error handling drift between consumers, and every
backend change risks silently breaking the frontend.

## Decision

1. **Contract document**: `docs/api.md` is the single source of truth for endpoints,
   request/response shapes, and examples. Any change requires a PR.
2. **Naming conventions** (apply to all new endpoints and fields):
   - plural nouns for resources, kebab-case for multi-word path segments;
   - snake_case JSON fields; lowercase enum values;
   - UUIDs as strings, datetimes as ISO 8601 UTC;
   - one error envelope everywhere: `{"error": {"code", "message", "details"}}`;
   - versioned prefix `/api/v1`; breaking changes get a new prefix, never in-place.
3. **Auth**: OAuth2 password flow (form-encoded login) issuing JWT bearer tokens.
4. **Degree vocabulary**: `degree_level` is `"bachelor"` or `"master"` only —
   enforced at the API boundary (422 on violation).

## Consequences

- B can generate typed clients / mock against `docs/api.md` without waiting for
  backend endpoints (upcoming shapes are marked frozen in the doc).
- C maps ingested data to the frozen `Opportunity` shape.
- Deviations discovered during integration are fixed via PR to the contract first.
