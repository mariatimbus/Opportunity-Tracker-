# Contributing

## Branch naming

- `chore/...` — repository/maintenance work
- `feat/...` — new features
- `fix/...` — bug fixes
- `docs/...` — documentation only

## Commit conventions

Conventional Commits: `type(scope): summary`, e.g. `feat(backend): design postgresql schema`.

## Pull requests

- Open PRs against `develop`; `main` is only updated from `develop` via release PRs.
- PR titles reference their issue: `type: summary (#N)`.
- PRs require: passing CI (ruff check + pytest), linked issue, and the checklist in the
  PR template completed.
- Do not merge your own PR — a teammate reviews and merges.
- Stacked branches are allowed: base a feature branch on another open feature branch
  and set the PR base accordingly.
