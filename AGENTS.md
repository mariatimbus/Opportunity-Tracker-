# AGENTS.md — Opportunity Tracker

These instructions apply to AI coding agents working in `mariatimbus/Opportunity-Tracker-`. Follow them unless the repository's current files or an explicit human instruction establish a safer, more recent rule. Do not assume that the status documented here proves the current GitHub state; inspect the repository before making changes.

## 1. Project and ownership

Opportunity Tracker is a platform for Bachelor's and Master's students to discover internships, research programs, scholarships, hackathons, conferences, and academic programs; determine eligibility; rank opportunities; and track applications.

- **Maria:** project lead, architecture, FastAPI/backend, security, AI/matching, integration, releases.
- **Bianca:** frontend and UX.
- **Dalia:** ingestion, opportunity data pipelines, Supabase data/schema work.
- **Target:** beta by **1 December 2026**; feature freeze **28 November 2026**.
- **Source of tasks:** Notion `Opportunity Tracker — Tasks`. Read the assigned task's goal, acceptance criteria, dependencies, owner, status, and expected branch before implementing.

## 2. Non-negotiable Git rules

1. `main` is for reviewed releases. `develop` is the normal integration branch.
2. **Never write, commit, or push directly to `main` or `develop`.**
3. **One task = one branch = one pull request.** Keep unrelated changes out of the PR.
4. Base new task branches on an up-to-date `develop`. Target ordinary PRs to `develop`, **not** `main`.
5. Follow naming conventions:
   - Maria: `feature/maria-<topic>`, `fix/maria-<topic>`, `chore/maria-<topic>`
   - Bianca: `feature/bianca-<topic>`, `fix/bianca-<topic>`, `chore/bianca-<topic>`
   - Dalia: `feature/dalia-<topic>`, `fix/dalia-<topic>`, `chore/dalia-<topic>`
   - Release: `release/<version>` (e.g. `release/1.0-beta`)
6. Use the branch specified in Notion when present. Legacy pre-convention branches need not be renamed.
7. Do not `push --force` to protected/shared branches, rewrite shared history, delete unrecognized code, or automatically resolve ambiguous merge conflicts.
8. Do not merge a PR without required human reviews and passing checks. **Agents must not self-approve, self-merge, or release without explicit authorization.**
9. Prefer **Squash and merge** for normal feature PRs, performed by the authorized human/reviewer. Delete the merged feature branch after confirmation.
10. Only Maria manages release PRs from `develop` to `main`.

### Before touching files

- Inspect `git status`, current branch, recent commits, relevant files, and repository documentation.
- Confirm task scope and dependencies. If work is blocked by another task or incomplete schema, **report the blocker**, do not invent a replacement architecture.
- Preserve uncommitted user changes. Never reset, checkout-over, clean, stash, or discard user work without permission.
- When authorized to use Git/network, typical start:

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b feature/maria-descriptive-task
git push -u origin feature/maria-descriptive-task
```

Use the correct assignee prefix and exact Notion branch. If the branch exists, check it out instead of recreating it.

### While implementing

- Make narrowly scoped, reversible changes. Commit logically and often **only when the human has requested commits**.
- Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `test(scope): ...`, `docs(scope): ...`, `refactor(scope): ...`, `chore(scope): ...`, `ci(scope): ...`.
- Preferred scopes: `web`, `backend`, `ingestion`, `ai`, `supabase`, `db`, `docs`.
- Run `git diff --check`, inspect the diff, and avoid unrelated formatting changes.
- Do not add dependencies, modify public API contracts, alter database security, or change infrastructure without explaining impacts and checking the task scope.
- Before review, sync your feature branch with `develop`; resolve straightforward conflicts carefully. Stop and escalate unclear conflicts rather than dropping another developer's work.

## 3. Architecture: Supabase-first

The project uses **Supabase Auth, hosted PostgreSQL, Storage, and Row Level Security (RLS)**. **FastAPI remains for privileged business logic, eligibility, matching, AI, and ingestion.** The older custom JWT auth, local PostgreSQL, and Alembic workflow are legacy; **do not extend them as the source of truth**.

- Supabase Auth is the **only** user identity provider. FastAPI should verify Supabase-issued identities/tokens, not create a parallel registration/JWT stack.
- Commit every schema/index/policy change as a reproducible SQL migration in `supabase/migrations/`. Do not rely on dashboard-only edits.
- Enforce RLS on user-owned data accessed from clients. Validate policies with at least two separate test users; never assume API/UI filtering replaces RLS.
- Frontend uses only browser-safe project URL and publishable/anon key. Keep service-role and privileged credentials **server-only**; never expose them in the browser, code, logs, screenshots, PRs, sample `.env`, or documentation.
- Use private Storage buckets for CVs and personal documents unless the team explicitly approves a different policy.
- Ingestion should be normalized, idempotent, deduplicated, and traceable to verified sources. Repeated runs must not create duplicates.
- Do not hard-code opportunities as an alternative to the Supabase-backed persistence layer except for clearly labeled fixtures or tests.
- The core product must operate without optional AI services; deterministic eligibility and matching come first.

## 4. Workstream responsibilities and tests

**Maria — FastAPI/backend/security/AI**

```bash
cd apps/api
uv sync
uv run pytest
uv run ruff check .
```

- Verify API inputs/outputs against agreed API contracts and tests.
- For auth/RLS/schema changes, test with the approved Supabase development or disposable test environment.
- Never bypass authorization by using elevated server credentials for ordinary per-user operations.

**Bianca — web/frontend**

- Use the actual scripts in `apps/web/package.json` for lint, typecheck, tests, and build; do not invent script names.
- Test changed UI on mobile and desktop.
- For auth/profile changes, test signup, login, logout, session restore, and forbidden access for a different user's data.
- Coordinate UI/API contract changes with Maria.

**Dalia — data/ingestion/Supabase**

- Run parser and normalization tests, plus a fixture dry run before live ingestion.
- Verify idempotency, duplicates, source reliability, URL/deadline correctness, and re-run behavior.
- Validate migrations and policies with test accounts; coordinate changes affecting API contracts with Maria.

If a command does not apply, say why. Never claim tests passed unless they actually ran and passed.

## 5. Pull requests and review

A PR must contain:

- The Notion task (and GitHub issue if present), scope, rationale, and behavior changed.
- Testing commands and **actual** results; mention tests that could not run.
- Screenshots for visible UI changes.
- Database migration and RLS/security notes, when relevant.
- Known limitations, backward compatibility considerations, and any deployment/configuration impact.

Default reviewers: Maria for backend, auth, database migrations/RLS, AI and architecture; Bianca for UI; Dalia for ingestion/data. Request reviewers from **both** impacted areas on cross-cutting changes. Do not merge with unresolved requested changes.

## 6. Definition of Done

A task is **Done only after all of these hold**:

- Task acceptance criteria met; dependencies and integration validated.
- Relevant tests/lint/typecheck/build pass; no conflict markers or debug code remain.
- API contracts/docs updated when behavior changes.
- Any Supabase migration and RLS changes committed and tested.
- No secrets leaked or privileged keys shipped to client code.
- PR reviewed, checks passing, and merged into `develop` by an authorized human.
- Notion status updated to `Done` once the merge is confirmed.

Before that, report it as **In Progress**, **Ready for Review**, or **Blocked**, accurately.

## 7. Agent autonomy and communication

- First respond with a brief plan: target task, files/modules likely affected, dependencies, tests, and intended branch.
- Implement only the explicitly requested scope; prefer minimal changes over rewrites.
- You may inspect/read files and run non-destructive local checks. **Ask for explicit authorization before pushing, opening/editing PRs, merging, deleting branches, modifying shared Supabase resources, or deploying** unless the human has already authorized the specific action.
- Do not update Notion task state based on assumptions. Verify the true repo/PR status first.
- At completion provide: changed files, summary of implementation, tests with results, blockers/risks, Git branch/commit/PR if actually created, and next recommended step.
- If an operation fails, report the real error; do not silently claim success or replace the user's workflow.

## 8. Release policy

Normal flow: **task branch → reviewed PR → `develop` → Maria-owned release PR → `main`**.

After the **28 November 2026** feature freeze, allow only approved release-blocking bug, security, or data fixes. The beta target is **1 December 2026**.

## 9. Mandatory leak and security check before every push

**No push may happen without a security pass first.** Before every `git push` (any branch), the agent MUST run and report:

1. **Secret scan of the exact diff being pushed** (`git diff origin/<base>...HEAD` plus untracked files to be added):
   - no private keys, API keys, JWT/service-role secrets, database connection strings, or passwords — including in tests, fixtures, seed data, `.env.example`, docs, and screenshots;
   - no real user data (emails, CVs, personal documents) in seeds or fixtures.
2. **History check** when commits already exist: `git log -p` over the new commits must not introduce secrets (a leaked secret is not fixed by a later delete — it needs rotation).
3. **Dependency check** when `pyproject.toml`, `uv.lock`, `package.json`, or lockfiles changed: run `pip-audit` (backend) / `npm audit` (frontend) against the new lockfile and report the result.
4. **Config/infra review** when CI, infrastructure, or deployment files changed: no hard-coded credentials, overly broad permissions, wildcard CORS with credentials, or privileged keys in client-side code.
5. Report the check results explicitly in the completion summary: what was scanned, what ran, and the outcome. If any check cannot run, say so — never claim the check passed when it did not run.

If a secret is found: stop, do not push, and report it to Maria immediately with the file and line.

## Frontend design system (mandatory)

- Keep every screen minimalist: generous whitespace, clear typography, restrained borders, simple layouts, and few visual accents. Avoid decorative gradients, heavy shadows, and unnecessary animation.
- Always respect the supplied brand palette. CSS tokens live in `apps/web/src/app/globals.css`; use semantic Tailwind utilities (`bg-background`, `text-foreground`, `text-muted`, `bg-primary`, `border-border`) instead of hard-coded colors in components.
- Palette: pale blue / Bleu pal `#C0C9E5`; lavender blue / Bleu lavanda `#B2BCDC`; electric blue / Albastru electric `#2862CF`; cobalt blue / Albastru cobalt `#2E46AA`; royal blue / Albastru regal `#1F3CA3`; indigo `#142A7B`; violet / Mov violet `#4A3F74`; navy / Bleumarin `#29263B`; warm white / Alb cald `#FFFBF0`.
- Default roles: warm white background/surface, navy main text, violet secondary text, electric blue primary actions, royal blue hover, lavender blue borders, cobalt blue focus ring. Pale/lavender blue are accents, not body text colors on light backgrounds.
- Preserve readable contrast, visible keyboard focus, semantic HTML, and responsive layouts. Respect reduced-motion preferences when adding animation. Do not introduce another palette or automatic dark theme without an explicit user request.

## 10. Reference

- Repository: https://github.com/mariatimbus/Opportunity-Tracker-
- Notion project plan: https://app.notion.com/p/3f688c98b3c0814294dbf4e8f8facfc3
- Notion tasks: https://app.notion.com/p/df1b16e458ed47b6ab74166c1b3c4a83
- GitHub Team Guide: https://app.notion.com/p/3f688c98b3c081a58ed1c4195ff8eb10
