# Opportunity Tracker web

Next.js App Router, strict TypeScript, Tailwind CSS v4, and ESLint. Requires Node.js 22+ and npm. From `apps/web`:

```sh
npm ci
npm run dev
```

Open http://localhost:3000. No environment variables or backend services are required for this initial page.

On Windows with nvm, run `nvm list` and activate an installed compatible version with `nvm use <version>` if `node --version` reports no active version. The local setup was verified with Node.js 24.22.0 and npm 11.19.1.

```sh
npm run lint
npm run typecheck
npm run build
npm start
```

`npm start` serves the production build. The initial page is a static introduction; discovery, authentication, and application tracking are not implemented yet.

## Theme

`src/app/globals.css` defines the nine brand colors and semantic roles with Tailwind v4 `@theme`. Prefer `bg-background`, `text-foreground`, `text-muted`, `bg-primary`, `text-on-primary`, and `border-border`. Radius tokens: `rounded-card` and `rounded-control`.

Keep the minimalist warm-white and blue theme on every screen. The mandatory palette and accessibility rules are documented in the repository's `AGENTS.md`.
