# ADR 0003: Supabase-first architecture

## Status

Accepted — supersedes the auth decision in [ADR 0002](0002-api-conventions.md)
(OAuth2 password flow with backend-issued JWTs).

## Context

The first backend milestone shipped custom authentication: the FastAPI app stored
bcrypt password hashes, ran `/auth/register` + `/auth/login`, and issued its own
HS256 JWTs signed with an app-level secret. That works for a demo but does not
scale into the platform we are building:

- **Auth is undifferentiated work.** Email verification, password reset, OAuth
  providers, session revocation, and brute-force protection are table stakes that
  Supabase Auth (GoTrue) provides out of the box.
- **The mobile app (`OppoPods/`) needs the same identity layer.** A hosted auth
  service with native SDKs (supabase-js, supabase-flutter) avoids re-implementing
  the login flow for every client.
- **Postgres is already the system's core.** Supabase gives us managed Postgres
  16, connection pooling, row-level security, and instant REST/realtime APIs on
  the same database the FastAPI backend uses, without adding a second data store.

## Decision

Supabase is the platform's identity and data backbone; the FastAPI backend is a
domain API on top of it.

1. **Supabase Auth is the only issuer of access tokens.** Clients (web, mobile)
   sign up and sign in directly against Supabase. The backend never sees
   passwords, never issues tokens, and `users.password_hash` is dropped (Alembic
   migration).
2. **The backend validates Supabase JWTs.** `Authorization: Bearer <token>` is
   verified against the project's JWT secret (`APP_SUPABASE_JWT_SECRET`), with
   `iss = {APP_SUPABASE_URL}/auth/v1` and `aud = "authenticated"` (`APP_SUPABASE_JWT_AUDIENCE`)
   enforced. Only `GET /api/v1/auth/me` remains; `/auth/register` and
   `/auth/login` are removed.
3. **Local `users` rows mirror auth identities.** On first authenticated request,
   the backend upserts a `users` row keyed by the JWT `sub` (the Supabase
   `auth.users` UUID) and bootstraps an empty profile, preserving the existing
   profile contract. The local row carries only domain state (`is_active`,
   `full_name` stays nullable); credentials live exclusively in Supabase.
4. **Database access stays through SQLAlchemy/Alembic** for the domain schema.
   Supabase hosts the Postgres cluster; migrations remain versioned in
   `database/migrations/` and are applied to the Supabase database. RLS policies
   may later enforce tenant isolation as a second line of defense, but the API is
   the primary enforcement point for business rules.
5. **Configuration** moves from `APP_JWT_SECRET_KEY`/`APP_JWT_EXPIRE_MINUTES` to
   `APP_SUPABASE_URL`, `APP_SUPABASE_JWT_SECRET`, and `APP_SUPABASE_JWT_AUDIENCE`
   (see `.env.example`).

## Consequences

- Clients integrate `supabase-js`/`supabase-flutter` for auth and hold the session;
  the backend treats any token Supabase signed as authoritative.
- Token expiry, refresh, and logout are Supabase's concern; the backend's 401
  surface shrinks to "token invalid/expired" (`unauthorized`).
- Adding OAuth providers, magic links, or email confirmation is a Supabase
  dashboard change, not backend work.
- Local dev runs against a Supabase project (cloud free tier or
  `supabase start` CLI); the SQLite fallback remains only for unit tests.
- Custom auth code (passlib, bcrypt, python-multipart) is removed, shrinking the
  dependency tree and the attack surface.
- If we ever outgrow Supabase Auth, the validation seam (`core/security.py:
decode_supabase_token`) is the only place that knows about the token format.
- **Revocation lag is inherent to stateless JWTs.** Banning a user in Supabase
  stops working only after their current access token expires (Supabase default
  ~1h); the local `is_active` flag covers users disabled in our own database.
  If that window matters for a feature, shorten the accepted token lifetime in
  Supabase rather than adding a revocation check to the backend.
