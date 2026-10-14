# Shared Supabase development

The shared development project is **opportunity-tracker-c1-test** in **eu-west-1**:
- Project ref: `fnldapsomswemayxhayk`
- URL: `https://fnldapsomswemayxhayk.supabase.co`
- Dashboard: https://supabase.com/dashboard/project/fnldapsomswemayxhayk

Dalia selected this project for team development. `opportunity-tracker` is a separate project; do not link or apply migrations there for this task.

## Join and connect

Maria/the organization owner must invite teammates to the Supabase organization/project. Each teammate logs in with their own account; do not share personal access tokens or passwords in Git/chat. Node.js 20+ and the repository-pinned Supabase CLI are required. From the repository root:

```sh
npm ci
npx supabase login
npx supabase link --project-ref fnldapsomswemayxhayk
npx supabase migration list --linked
```

The database password prompt is private. `.temp/` contains local link state and is ignored. `config.toml` configures the optional local stack, not the hosted project's Auth settings.

Copy `.env.example` to `.env`. For the backend, set `DATABASE_URL` to the SQLAlchemy psycopg connection string from **Connect** in the dashboard: use `postgresql+psycopg://` and SSL (`?sslmode=require`). Use the session pooler if direct IPv6 is unavailable. Keep the password URL-encoded and server-only. SQLite is a unit-test/offline fallback, not the shared team database. Run backend commands from the repository root with `uv run --project apps/api ...` so the root `.env` is loaded.

For Bianca's web app, use the same project URL and the **publishable** key (or legacy anon key) in `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. They are browser-safe; `service_role`, database passwords, JWT secrets and personal access tokens must never have a `NEXT_PUBLIC_` prefix. The web app is currently a placeholder; configure its Supabase client when implementing it, with these variable names. Signup/login go through Supabase Auth, not a backend password endpoint.

The committed minimal hosted config in `supabase/hosted/supabase/config.toml` declares the development site URL as `http://localhost:3000` and explicitly allow `http://localhost:3000/auth/callback`. Add only the team's actual preview URLs when needed. Enable email/password signup and email confirmation; configure SMTP before expecting production email delivery. Apply only the hosted configuration with `npx supabase config diff --workdir supabase/hosted --project-ref fnldapsomswemayxhayk`, then `npx supabase config push --workdir supabase/hosted --project-ref fnldapsomswemayxhayk`. Undeclared hosted settings remain unchanged. The local stack configuration does not configure hosted Auth automatically.

This project uses ES256. The backend verifies ES256/RS256 tokens against the configured project JWKS, with issuer/audience/expiry checks and cached public keys. No JWT secret is needed for this project. Legacy HS256 is accepted only when a server-side secret is explicitly configured. Never change project signing keys to work around validation failures.

## Versioned schema

`supabase/migrations/` is the schema/policy source of truth. The legacy Alembic files remain as historical references; do not run `alembic upgrade head` against this Supabase project. The former Docker/Postgres compose stack is not needed for normal team development.

1. `20261014175810_initial_schema.sql`: translates the existing models and Alembic degree-field/password-removal/email-index changes; seven domain tables, foreign keys, uniqueness, enums, indexes and timestamp triggers. Identity references `auth.users(id)`.
2. `20261014181551_rls_policies.sql`: explicit grants and ownership policies.
3. `20261014190000_auth_user_sync.sql`: Auth signup/update synchronization, existing-user backfill, automatic profiles and server ingestion grants.

The first two migrations were already applied before this change and are preserved. Opportunity SQL enum values `fellowship` and `early_program` extend the current ORM enum: ingesting those values through SQL requires corresponding ORM reconciliation before exposing them through backend code. Seed import and further opportunity schema reconciliation belong to separate tasks; seed fixtures are not imported automatically.

For a **fresh hosted Supabase project**, create it in the approved team organization, then:

```sh
npx supabase link --project-ref <fresh-project-ref>
npx supabase db push --dry-run
npx supabase db push
npx supabase migration list --linked
npm run db:test
```

Supabase provisions its own Auth schemas/roles; the migrations then create the application schema. Never reset the shared development database. For an optional disposable local Supabase stack (Docker required):

```sh
npx supabase start
npx supabase db reset --local
npx supabase db query --local --file supabase/tests/rls.sql
```

For later schema edits create a new migration, review the SQL, preview and apply it. Do not edit already applied migration files or rely on SQL Editor-only changes.

## Security review for Maria

| Table | Browser access |
| --- | --- |
| users | Authenticated owner SELECT only; Auth trigger owns identity updates |
| profiles | Owner SELECT/INSERT/UPDATE with both USING and WITH CHECK |
| applications | Owner SELECT/INSERT/UPDATE/DELETE |
| user_skills | Owner SELECT/INSERT/DELETE |
| skills, opportunities, opportunity_skills | Anonymous/authenticated SELECT only |

All seven tables enable RLS. Ownership uses `auth.uid()`, not editable metadata. Server ingestion uses a privileged server connection/service role; those bypass RLS and must enforce authorization in backend business logic. The Auth sync function is in an unexposed private schema, uses an empty search path and has no browser/PUBLIC EXECUTE privilege. Auth deletion cascades through identity/profile/application/skill links. `is_active` is server-managed and cannot be edited through browser roles. No CV Storage bucket is created by this task; keep any future CV bucket private.

`npm run db:test` uses two synthetic Auth users and rolls back all fixtures. It checks owner access, cross-user visibility/writes, anonymous access, catalog writes, Auth bootstrap/email sync and deletion cascades. Maria must review the SQL/policies and grants before approval. Bianca must verify a real signup/login and own-profile request with the publishable key after receiving organization access.

## Validation recorded

- All migrations replayed on fresh PostgreSQL using PGlite (Supabase-managed Auth/role interfaces stubbed), then the RLS suite passed. Run `npm run db:test:fresh` without Docker.
- All three migrations applied on the chosen hosted project; `npm run db:test` passed and fixtures rolled back.
- Hosted Auth config preview has no remaining declared changes; security advisors reported no issues.
- Full Supabase local-stack reset was not run: Docker Desktop returned HTTP 500. PGlite validates application SQL, not the complete Supabase infrastructure.
- Maria review, invitations and Bianca's browser signup/login verification remain human integration steps.
