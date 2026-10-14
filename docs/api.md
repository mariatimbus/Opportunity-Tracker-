# API Contract

Frozen endpoint contract for the Opportunity Intelligence Platform backend.
Consumers: **B** (frontend, `apps/web`) and **C** (data/ingestion, `services/ingestion`).
Conventions are decided in [ADR 0002](decisions/0002-api-conventions.md); changes to this
document require a PR and sign-off from B and C.

- Base URL: `http://localhost:8000`
- Version prefix: `/api/v1` (breaking changes ship under a new prefix)
- Interactive OpenAPI docs: `/docs` (Swagger UI), `/openapi.json`
- Health probes (unversioned): `GET /health`, `GET /health/db`

## Conventions

- **Auth**: `Authorization: Bearer <access_token>` on all endpoints marked 🔒.
  Tokens are issued by **Supabase Auth** (client-side sign-in), not by this API —
  see [ADR 0003](decisions/0003-supabase-first-architecture.md). The backend
  validates signature, `iss`, `aud`, and expiry; an unknown-but-valid identity
  is mirrored into a local `users` row on first call.
- **Paths**: plural nouns; multi-word segments use kebab-case (`/job-fairs`).
- **Fields**: snake_case in JSON; UUIDs as strings; datetimes ISO 8601 UTC (`2026-10-07T12:00:00Z`).
- **Enums**: lowercase string values (`bachelor`, `internship`, `applied`).
- Money/durations: plain numbers with the unit in the field name (`salary_eur`, `expires_in`).
- Empty collections serialize as `[]`, absent nullable fields as `null` (never omitted).

## Error envelope

Every non-2xx response (including framework validation failures):

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Invalid email or password",
    "details": null
  }
}
```

| HTTP | code | When |
| --- | --- | --- |
| 401 | `unauthorized` | missing/invalid/expired token |
| 403 | `account_disabled` | deactivated user |
| 404 | `not_found` | unknown route |
| 404 | `skill_not_found` | skill not attached to profile |
| 429 | `rate_limited` | per-IP rate limit exceeded (see `APP_RATE_LIMIT_PER_MINUTE`) |
| 422 | `validation_error` | schema validation (details = pydantic errors) |

## Auth

Sign-up and sign-in happen **client-side against Supabase Auth**; this API never
accepts passwords and never issues tokens. Clients send the Supabase access
token as a bearer token. The error codes `invalid_credentials` and `email_taken`
from the previous contract no longer exist — Supabase returns its own errors
for sign-in/sign-up failures.

### GET /api/v1/auth/me 🔒

Returns the caller's user record, creating it (plus an empty profile) from the
token claims on first authenticated call.

```json
{"id": "9f1c…", "email": "ada@example.com", "full_name": null, "is_active": true}
```

## Profile 🔒

Bachelor/Master rules enforced on write: `degree_level` must be `"bachelor"` or
`"master"`; `graduation_year` must be 1900–2100. Violations → 422.

### GET /api/v1/profile

Returns the caller's profile, bootstrapping an empty one on first call. `201` never
occurs here — the resource always exists for an authenticated user.

```json
{
  "id": "3fa8…", "user_id": "9f1c…",
  "headline": null, "bio": null, "location": null, "resume_url": null,
  "degree_level": null, "field_of_study": null, "university": null, "graduation_year": null,
  "created_at": "2026-10-07T12:00:00Z", "updated_at": "2026-10-07T12:00:00Z"
}
```

### PUT /api/v1/profile

Full replacement — **omitted fields are cleared to null**.

```json
// request
{
  "headline": "CS Master student",
  "location": "Berlin",
  "degree_level": "master",
  "field_of_study": "Computer Science",
  "university": "TU Berlin",
  "graduation_year": 2027
}
// 200 — full ProfileResponse as above
```

### PATCH /api/v1/profile

Partial update — only sent fields change; send `null` explicitly to clear one field.

```json
// request
{"graduation_year": 2028}
```

## Skills & interests 🔒

Skills on a profile double as the user's interests. Names are trimmed, lowercased,
and deduplicated; unknown names create new skill rows (get-or-create).

### GET /api/v1/profile/skills

```json
[{"id": "7b2d…", "name": "python"}, {"id": "c4e1…", "name": "sql"}]
```

### PUT /api/v1/profile/skills — replace the whole set

```json
// request
{"names": ["Python", "SQL", "python"]}
// 200
[{"id": "7b2d…", "name": "python"}, {"id": "c4e1…", "name": "sql"}]
```

### POST /api/v1/profile/skills — add one (idempotent)

```json
// request
{"name": "Go"}   // 201
```

### DELETE /api/v1/profile/skills/{name}

`200` with the remaining skills; `404 skill_not_found` if not attached.

### GET /api/v1/skills — catalog of all skills (for pickers)

## Frozen upcoming contracts

Implemented in a later phase; the shapes below are frozen so B and C can build
against them now. They mirror the SQLAlchemy models in `apps/api/src/opportunity_api/models/`.

### GET /api/v1/opportunities · GET /api/v1/opportunities/{id}

```json
{
  "id": "1d9a…",
  "title": "Backend Intern",
  "description": "…",
  "organization": "Example Corp",
  "opportunity_type": "internship",
  "location": "Berlin",
  "url": "https://example.com/job/1",
  "source": "example",
  "source_id": "1",
  "deadline": "2026-11-30T23:59:59Z",
  "posted_at": "2026-10-01T09:00:00Z",
  "is_active": true,
  "skills": [{"id": "7b2d…", "name": "python"}]
}
```

`opportunity_type` ∈ `internship | job | research | scholarship | fellowship | hackathon | competition | early_career | open_source | grant | other` — final vocabulary decided 2026-10-14 (Maria, option A); single source of truth shared with `supabase/migrations` and `database/seeds`.

### GET /api/v1/applications · POST /api/v1/applications · PATCH /api/v1/applications/{id}

```json
{
  "id": "5c3f…",
  "opportunity_id": "1d9a…",
  "status": "applied",
  "notes": "via referral",
  "applied_at": "2026-10-05T14:00:00Z",
  "created_at": "2026-10-05T14:00:00Z",
  "updated_at": "2026-10-05T14:00:00Z"
}
```

`status` ∈ `saved | applied | interview | offer | rejected`. One application per
(user, opportunity) — duplicates → 409.

## Changelog

- 2026-10-07 — frozen v1 contract after A4/A5 landed (auth, profile, skills).
- 2026-10-14 — auth moved to Supabase per ADR 0003: `POST /auth/register` and
  `POST /auth/login` removed; tokens are Supabase-issued; `invalid_credentials`
  and `email_taken` error codes retired. Per-IP rate limiting added
  (`429 rate_limited`, `APP_RATE_LIMIT_PER_MINUTE`, default 240/min).
- 2026-10-14 — `opportunity_type` final vocabulary (11 values) — additive
  extension plus renames: adds `research`, `competition`, `open_source`;
  `early_program` renamed to `early_career`. Aligns contract, Supabase enum,
  FastAPI model, and seed dataset. Pending B (frontend) and C (data) sign-off
  per ADR 0002.
