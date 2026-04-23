# AGENTS.md

Scope: `ui/admin/`

## Purpose

This directory contains the ChatMock browser admin UI.

Use repo-local docs first for ChatMock-specific behavior:

- `docs/chatmock-admin-ui-architecture.md`
- `docs/chatmock-admin-ui-frontend-conventions.md`
- `docs/chatmock-instance-management.md`
- `DOCKER.md`

Use Context7 for current third-party library APIs:

- React Router
- TanStack Query
- React Hook Form
- shadcn/ui

## Boundary Rules

- Treat `src/App.tsx` as the admin orchestration/provider boundary, not a presentational leaf.
- Treat `src/router.tsx` and `src/layouts/AdminLayout.tsx` as route and shell ownership only.
- Treat `src/lib/query/` and `src/lib/api/client.ts` as the server-state and request boundary.
- Treat `src/lib/settings/provider.tsx` as the browser-local preview/apply/reset boundary for theme and code-size preferences.
- Treat `src/lib/settings/` as the browser-local settings domain for types, storage, and theme presets.
- Treat `src/forms/` as typed form adapters, not network or layout code.
- Treat `src/components/ui/` as repo-owned copied primitives. Upstream shadcn docs are reference material, but local component files are the real source of truth.
- Treat `src/components/shared/` as the ChatMock normalization layer for repeated operator-facing wrappers and patterns.

## Working Rules

- Preserve the operator-first route structure:
  - `Current State`
  - `Edit Config`
  - `Prompt Files`
  - `Settings`
- Keep prompt-file editing separate from draft/apply structural config flows.
- Keep browser-local settings separate from backend admin config. Theme presets and preview state live in the settings layer and local CSS, not in server-side config.
- Do not add a second browser auth/session model without explicit approval.
- When changing route structure, component layers, or SPA packaging/runtime paths, update `docs/chatmock-admin-ui-architecture.md` in the same branch.

## Verification

Useful checks from repo root:

```bash
./.venv/bin/python -m pytest tests/test_admin_routes.py -q
./.venv/bin/python -m pytest tests/test_routes.py -q
cd ui/admin && npm test
cd ui/admin && npm run build
```
