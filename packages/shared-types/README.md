# packages/shared-types

Shared TypeScript types between the web app and other consumers.

The backend contract is frozen in [`docs/api.md`](../../docs/api.md) (see
[ADR 0002](../../docs/decisions/0002-api-conventions.md) for conventions). Types in
this package must mirror that contract; snake_case JSON fields map to camelCase
TypeScript properties at the client boundary.
