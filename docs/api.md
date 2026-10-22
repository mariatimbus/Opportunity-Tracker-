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
| 404 | `opportunity_not_found` | unknown opportunity id on application create |
| 404 | `application_not_found` | unknown id, or owned by another user (indistinguishable) |
| 409 | `application_exists` | opportunity already tracked by this user |
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

## Opportunities

Implemented in A7 (read-only catalog). Ordered by `posted_at` descending,
unposted opportunities last.

### GET /api/v1/opportunities

Query params (all optional, combined with AND):

| Param | Type | Rule |
| --- | --- | --- |
| `page` | int | default `1`, ≥ 1 |
| `page_size` | int | default `20`, 1–100 |
| `opportunity_type` | enum | one of the 11 vocabulary values |
| `degree_level` | enum | `bachelor`/`master` match themselves **and** `both`; `null` (unknown) never matches |
| `study_year` | int (1–6) | containment: opportunity's `study_year` must include it; `null` (unknown) never matches |
| `location` | string | case-insensitive substring |
| `is_active` | bool | exact match |
| `deadline_after` / `deadline_before` | datetime ISO 8601 | inclusive bounds on `deadline` |
| `search` | string | case-insensitive substring of `title`, `organization`, or `description` |

```json
// 200
{
  "items": [{"id": "1d9a…", "title": "Backend Intern", "…": "…"}],
  "page": 1,
  "page_size": 20,
  "total": 50
}
```

Item shape (same as the detail endpoint):

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
  "degree_level": "both",
  "study_year": [2, 3],
  "skills": [{"id": "7b2d…", "name": "python"}]
}
```

`opportunity_type` ∈ `internship | job | research | scholarship | fellowship | hackathon | competition | early_career | open_source | grant | other` — final vocabulary decided 2026-10-14 (Maria, option A); single source of truth shared with `supabase/migrations` and `database/seeds`.

`degree_level` ∈ `bachelor | master | both`, nullable — eligibility, not the caller's own degree; `null` means not established (never "everyone"). `study_year` is a nullable array of eligible study years (e.g. `[2, 3]`); `null` means not established.

### GET /api/v1/opportunities/{id}

`200` with the item shape above; `404 not_found` for a valid but unknown id;
`422 validation_error` for a malformed UUID.

### GET /api/v1/opportunities/{id}/eligibility 🔒

A9 eligibility assessment of the opportunity against the caller's profile
(full rule set: degree level, study year, graduation year, location — every
rule reports `eligible | possibly_eligible | not_eligible | unknown` with a
human-readable reason; facts the source never stated stay `unknown`).

```json
// 200
{
  "status": "possibly_eligible",
  "reasons": [
    { "rule": "degree_level", "status": "eligible", "reason": "Bachelor students are accepted" },
    { "rule": "study_year", "status": "unknown", "reason": "Student study year is not known" },
    { "rule": "graduation_year", "status": "unknown", "reason": "No structured graduation restriction available" },
    { "rule": "location", "status": "eligible", "reason": "Remote opportunity; no location barrier" }
  ]
}
```

The profile currently carries `degree_level`, `graduation_year` and
`location`; `study_year` has no profile field yet, so that rule is always
`unknown` until the schema grows.

### GET /api/v1/opportunities/{id}/match 🔒

A10 explainable match score, gated by A9 eligibility (degree level, study
year, location rules only — graduation cannot gate matching without a
structured source). `not_eligible` always scores `0`;
`possibly_eligible`/`unknown` caps the score at `49`; `eligible` is
uncapped (max 100). The optional `ai` component (A11/A12, Ollama
embeddings) is `0` when Ollama is not configured — the deterministic core
is the product, AI is a bonus.

```json
// 200
{
  "score": 54,
  "eligibility": "eligible",
  "components": { "skills": 12, "field_fit": 25, "interests": 10, "location": 7, "ai": 0 },
  "reasons": ["Skill overlap: Python, SQL", "Field of study matches: computer science", "Remote-friendly location"]
}
```

Both endpoints: `401 unauthorized` without a bearer token; `404 not_found`
for a valid but unknown id.

## Applications 🔒

Implemented in A8 (saved opportunities + application tracking). All endpoints
require a bearer token and are scoped to the current user — an application
owned by another user is indistinguishable from a missing one (`404`, never
`403`), mirroring the Supabase RLS policy (defense in depth). `user_id` is
never exposed in responses.

### GET /api/v1/applications

List of the caller's applications, newest first. Optional query param
`status` (`saved|applied|interview|offer|rejected`) filters by status.

```json
// 200
{
  "items": [{ "…": "application shape below" }],
  "total": 2
}
```

### POST /api/v1/applications

Saves an opportunity (default status `saved`).

```json
// request
{"opportunity_id": "1d9a…"}
```

`201` with the application shape; `404 opportunity_not_found` if the
opportunity does not exist; `409 application_exists` if it is already tracked
(one application per (user, opportunity)). An explicit `status`, `notes`, or
`applied_at` may be sent on create.

### PATCH /api/v1/applications/{id}

Updates `status`, `notes`, and/or `applied_at` (only sent fields change).
When the status becomes `applied` and no `applied_at` was provided, the server
stamps the current time. `404 application_not_found` for an unknown id or one
owned by another user.

### DELETE /api/v1/applications/{id}

Removes the application from the tracker. `204` on success; `404` for an
unknown id or one owned by another user.

Application shape (all endpoints):

```json
{
  "id": "5c3f…",
  "opportunity_id": "1d9a…",
  "status": "applied",
  "notes": "via referral",
  "applied_at": "2026-10-05T14:00:00Z",
  "created_at": "2026-10-05T14:00:00Z",
  "updated_at": "2026-10-05T14:00:00Z",
  "opportunity": {
    "id": "1d9a…",
    "title": "Backend Intern",
    "organization": "Example Corp",
    "opportunity_type": "internship",
    "deadline": "2026-11-30T23:59:59Z"
  }
}
```

`status` ∈ `saved | applied | interview | offer | rejected`. `opportunity` is
an embedded summary so the tracker UI renders without extra lookups.

## Frozen upcoming contracts

Implemented in a later phase; the shapes below are frozen so B and C can build
against them now. They mirror the SQLAlchemy models in `apps/api/src/opportunity_api/models/`.

(none — applications moved out on 2026-10-15)

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
- 2026-10-14 — opportunities gain nullable `degree_level`
  (`bachelor|master|both`) and `study_year` (array of ints) eligibility
  fields, backing the seed dataset. Additive; pending B/C sign-off.
- 2026-10-15 — A7: `GET /api/v1/opportunities` (pagination + filters) and
  `GET /api/v1/opportunities/{id}` implemented per the frozen shape; moved out
  of „Frozen upcoming contracts". Query params documented above; pending B/C
  sign-off.
- 2026-10-15 — A8: applications endpoints implemented
  (`GET/POST /api/v1/applications`, `PATCH/DELETE /api/v1/applications/{id}`);
  moved out of „Frozen upcoming contracts". Responses embed an `opportunity`
  summary; `applied_at` is auto-stamped on the transition to `applied`;
  pending B/C sign-off.
- 2026-10-22 — A9/A10/A11: `GET /api/v1/opportunities/{id}/eligibility` (A9
  rule-by-rule eligibility with reasons) and `GET /api/v1/opportunities/{id}/match`
  (explainable score gated by eligibility; optional Ollama `ai` component via
  `APP_OLLAMA_URL`, deterministic-only when unset). Profile-driven:
  `study_year` and `interests` are not profile fields yet, so the study-year
  rule stays `unknown` and the interests component is always 0 until the
  profile schema grows; pending B/C sign-off.
