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

## API environment configuration

From `apps/web`, create your local configuration in PowerShell:

```powershell
Copy-Item -LiteralPath .env.example -Destination .env.local -ErrorAction Stop -Confirm
```

If `.env.local` already exists, edit it instead of copying over it. The local file is ignored by Git; `.env.example` is the shared template. Next.js loads environment files from `apps/web`, not from the monorepo root or `src`.

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, without the `/api/v1` prefix. Future requests will add their endpoint paths, such as `/api/v1/opportunities` or `/health`.

`src/lib/env.ts` exports `API_BASE_URL`. It reads `process.env.NEXT_PUBLIC_API_BASE_URL` directly so Next.js can inline it into browser code, requires an absolute HTTP or HTTPS URL, and removes trailing slashes. Missing, blank, or invalid values throw a clear error when the module is imported; errors do not include the supplied value. The initial page does not import this module or make API requests, so it still runs without configuration or a backend.

The `NEXT_PUBLIC_` prefix makes the value public: never put credentials or secret keys in it. Restart `npm run dev` after changing `.env.local`. For production, set the variable in the build environment before `npm run build`; changing it after the build requires rebuilding the application.

## App shell

`src/app/layout.tsx` provides the shared responsive container, header, main content area, and footer. The application name and the Home link in the main navigation use Next.js `Link` and lead to `/`, the only current page. The keyboard-accessible Skip to content link moves focus to the single `main-content` landmark.

`src/app/page.tsx` contains only the introductory content and its page-specific spacing. The shell fills at least the viewport height, with the footer following the content on taller pages. Styling uses the existing theme tokens and visible keyboard focus styles.

## Theme

`src/app/globals.css` defines the nine brand colors and semantic roles with Tailwind v4 `@theme`. Prefer `bg-background`, `text-foreground`, `text-muted`, `bg-primary`, `text-on-primary`, and `border-border`. Radius tokens: `rounded-card` and `rounded-control`.

Keep the minimalist warm-white and blue theme on every screen. The mandatory palette and accessibility rules are documented in the repository's `AGENTS.md`.
