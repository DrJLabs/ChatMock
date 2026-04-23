# ChatMock Admin UI Stack Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the ChatMock admin UI from the current minimal React + Vite + custom CSS setup to a scalable stack centered on React Router v7, Tailwind CSS v4, shadcn/ui, TanStack Query, and React Hook Form, while keeping boundaries clear and avoiding unnecessary complexity.

**Architecture:** Introduce the stack in phases so each layer replaces a current weakness without creating overlapping abstractions. React Router owns routes and layout, TanStack Query owns server state, React Hook Form owns forms, and Zustand is deferred until a specific UI-only state problem appears.

**Tech Stack:** React 18, Vite, TypeScript, React Router v7, Tailwind CSS v4, shadcn/ui, TanStack Query, React Hook Form, existing Flask admin API

---

## File Structure

### Existing UI files that will likely change over the migration

- Modify: `ui/admin/package.json`
  - Add frontend dependencies in phases.
- Modify: `ui/admin/src/main.tsx`
  - Add router and QueryClient providers.
- Modify: `ui/admin/src/App.tsx`
  - Likely shrink into route layout composition or be replaced entirely.
- Modify: `ui/admin/src/styles.css`
  - Transition out of the current custom stylesheet as Tailwind lands.
- Modify: `ui/admin/index.html`
  - Minimal support changes only if needed for theme/font/runtime shell.

### Likely new files introduced by the migration

- Create: `ui/admin/src/router.tsx`
  - Central React Router route definitions.
- Create: `ui/admin/src/layouts/AdminLayout.tsx`
  - Shared app shell under Router.
- Create: `ui/admin/src/lib/query-client.ts`
  - Shared TanStack Query client configuration.
- Create: `ui/admin/src/lib/query/`
  - Query/mutation hooks per backend resource.
- Create: `ui/admin/src/components/ui/`
  - shadcn/ui component outputs.
- Create: `ui/admin/src/components/shared/`
  - Local wrapper components to prevent shadcn drift.
- Create: `ui/admin/src/forms/`
  - React Hook Form schemas and adapters for config forms.
- Create: `ui/admin/src/routes/`
  - Route-level page entry files for `Current State`, `Edit Config`, `Prompt Files`.
- Create: `ui/admin/src/lib/theme/`
  - Optional later theme toggle and mode helpers.

## Migration Rules

These rules are part of the plan and should be treated as constraints:

1. React Router handles routing and layout only.
2. TanStack Query handles backend/server state.
3. React Hook Form handles form state.
4. Zustand is not introduced until a specific UI-only state problem is identified.
5. Route loaders/actions are not the primary data layer while TanStack Query is present.
6. shadcn/ui components should be normalized through local usage patterns instead of copied arbitrarily.

## Task 1: Establish the route/layout foundation

**Files:**
- Modify: `ui/admin/package.json`
- Modify: `ui/admin/src/main.tsx`
- Modify or replace: `ui/admin/src/App.tsx`
- Create: `ui/admin/src/router.tsx`
- Create: `ui/admin/src/layouts/AdminLayout.tsx`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Add React Router v7**

Add the dependency:

```bash
cd ui/admin
npm install react-router
```

Expected: `package.json` and lockfile updated successfully.

- [ ] **Step 2: Create a router definition**

Define routes for:

- `/admin/ui`
- `/admin/ui/edit-config`
- `/admin/ui/prompt-files`

Use Declarative or Data mode primitives only. Do not adopt Framework mode.

- [ ] **Step 3: Move the shared shell into a route layout**

Create `AdminLayout.tsx` to own:

- the header
- the top-level nav
- common app chrome

- [ ] **Step 4: Mount the router in `main.tsx`**

Wrap the app with `<RouterProvider>` or `<BrowserRouter>`-based routing, depending on the chosen v7 mode.

- [ ] **Step 5: Rebuild**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 2: Introduce Tailwind CSS v4 and replace the shared stylesheet foundation

**Files:**
- Modify: `ui/admin/package.json`
- Modify: `ui/admin/src/main.tsx` or Tailwind entry CSS
- Modify or replace: `ui/admin/src/styles.css`
- Create: Tailwind v4 CSS entry/config files as required by the official setup
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Install Tailwind CSS v4**

Add the required Tailwind packages using the current official Vite-compatible setup.

- [ ] **Step 2: Create the Tailwind entry CSS**

Use the v4 CSS-first model rather than building around an older `tailwind.config.js` mental model unless a config file is explicitly needed.

- [ ] **Step 3: Port the current shell tokens into Tailwind theme variables**

Carry over:

- current dark navy shell direction
- current light surfaces
- existing spacing and radius decisions

- [ ] **Step 4: Replace the core shell/layout classes first**

Do not rewrite every page at once. Start with:

- app shell
- header
- nav
- shared cards
- button variants

- [ ] **Step 5: Rebuild**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 3: Add shadcn/ui as the component baseline

**Files:**
- Modify: `ui/admin/package.json`
- Create: `ui/admin/components.json` or equivalent shadcn config output
- Create: `ui/admin/src/components/ui/`
- Create: `ui/admin/src/components/shared/`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Initialize shadcn/ui for the Vite app**

Use the supported Vite setup path rather than a manual copy-first approach.

- [ ] **Step 2: Add only the components the UI already clearly needs**

Start with likely primitives such as:

- button
- card
- input
- textarea
- select
- tabs or segmented control
- dialog if later needed

- [ ] **Step 3: Create local wrapper conventions**

Do not let page files import random raw generated components everywhere without a pattern. Establish a small shared layer for repeated variants.

- [ ] **Step 4: Replace existing shared shell primitives**

Use shadcn-backed components where it reduces repetition; do not churn working page-specific structures without a clear gain.

- [ ] **Step 5: Rebuild**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 4: Migrate server state to TanStack Query

**Files:**
- Modify: `ui/admin/package.json`
- Modify: `ui/admin/src/main.tsx`
- Create: `ui/admin/src/lib/query-client.ts`
- Create: `ui/admin/src/lib/query/*.ts`
- Modify: route/page files currently calling `fetch` directly
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Install TanStack Query**

Add:

```bash
cd ui/admin
npm install @tanstack/react-query
```

- [ ] **Step 2: Create the shared QueryClient**

Add one app-level client with conservative defaults appropriate for an operator console.

- [ ] **Step 3: Add one query hook per backend resource**

Start with:

- prompt state
- profiles
- instances
- draft state
- runtime validation

- [ ] **Step 4: Add one mutation hook per mutation family**

Start with:

- draft profile mutations
- draft instance mutations
- draft apply/reset/validate/preview
- prompt reload
- prompt file read/write
- redeploy

- [ ] **Step 5: Replace manual fetch orchestration in the pages**

Page components should stop manually juggling request lifecycle for server resources once hooks are in place.

- [ ] **Step 6: Rebuild**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 5: Move structural forms to React Hook Form

**Files:**
- Modify: `ui/admin/package.json`
- Create: `ui/admin/src/forms/`
- Modify: `ui/admin/src/features/profiles/ProfilesPage.tsx`
- Modify: `ui/admin/src/features/instances/InstancesPage.tsx`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Install React Hook Form**

Add:

```bash
cd ui/admin
npm install react-hook-form
```

- [ ] **Step 2: Create typed form models for profile and instance editors**

Keep them aligned with the existing backend contracts and validation expectations.

- [ ] **Step 3: Convert the profile editor**

Replace manual field state with RHF for:

- registration
- submission
- dirty handling
- validation feedback

- [ ] **Step 4: Convert the instance editor**

Do the same for the instance editor, keeping Advanced fields behind disclosures.

- [ ] **Step 5: Rebuild**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 6: Reassess whether Zustand is needed

**Files:**
- Potentially create later: `ui/admin/src/stores/`
- Test: no code change required if not justified

- [ ] **Step 1: Inventory remaining client-only state after Router + Query + RHF**

Look specifically for:

- theme selection
- view preferences
- drawer state
- transient search/filter state

- [ ] **Step 2: Do not add Zustand if local state is still sufficient**

If no meaningful problem remains, stop here.

- [ ] **Step 3: If a real need exists, add Zustand only for that narrow concern**

Do not use it for:

- fetched server resources
- mutation state
- form state

## Task 7: Final policy verification

**Files:**
- Modify if needed: `docs/chatmock-admin-ui-stack-evaluation.md`
- Create if useful later: `docs/chatmock-admin-ui-frontend-conventions.md`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Verify the migration still honors the stack boundaries**

Check that:

- routing logic is not masquerading as server-state management
- query hooks own backend state
- forms own input state
- Zustand has not become an accidental second app architecture

- [ ] **Step 2: Run the frontend build**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

- [ ] **Step 3: Run the backend regression suite**

Run:

```bash
/home/drj/tools/chatmock/.venv/bin/python -m pytest tests/test_admin_routes.py tests/test_admin_draft_service.py tests/test_profile_registry.py tests/test_instance_registry.py tests/test_instance_service.py tests/test_routes.py tests/test_cli.py -q
```

Expected: PASS

## Recommended Execution Strategy

This migration should not be done as one giant change. The safest order is:

1. React Router v7
2. Tailwind CSS v4
3. shadcn/ui
4. TanStack Query
5. React Hook Form
6. Zustand only if justified

That order minimizes overlap and keeps each phase easy to verify independently.
