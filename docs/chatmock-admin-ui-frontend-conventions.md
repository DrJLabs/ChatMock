# ChatMock Admin UI Frontend Conventions

## Date

2026-04-23

## Purpose

Capture the stack boundaries after the admin UI migration so future work keeps the layers separate.

## Active Stack Boundaries

- React Router owns route definitions and shared layout composition.
- TanStack Query owns server-state reads, cache invalidation, and mutation lifecycles.
- React Hook Form owns structural editor form state and validation.
- shadcn/ui provides the primitive component layer.
- `src/components/shared/` is the local normalization layer for repeated ChatMock-specific wrappers and variants.

## File-Level Conventions

- Routes live in `ui/admin/src/router.tsx` and `ui/admin/src/routes/`.
- Query client setup lives in `ui/admin/src/lib/query-client.ts`.
- Query hooks live in `ui/admin/src/lib/query/`.
- Typed form adapters live in `ui/admin/src/forms/`.
- Shared app chrome and operator-card wrappers live in `ui/admin/src/layouts/` and `ui/admin/src/components/shared/`.

## Zustand Decision

Do not add Zustand right now.

Current remaining client-only state is still narrow and local:

- current editor selection
- create-vs-edit mode
- prompt file text being edited before save
- transient status messaging

That state does not justify a global client-store layer yet. If a future UI-only concern appears that genuinely spans routes or many unrelated components, evaluate Zustand only for that specific problem.
