# ChatMock Admin UI Architecture

## Purpose

Document the current browser-admin UI composition so future work keeps the boundaries between routing, data access, feature pages, and local component layers explicit.

This is the source of truth for the repo-owned admin UI shape. Use upstream library docs for third-party APIs, but use this file first when the question is about how ChatMock itself is assembled.

## Runtime Shape

- Browser entrypoint: `GET /admin/ui`
- SPA basename: `/admin/ui`
- Backend API base: same-origin `/admin/*`
- Trust model: no second browser auth layer; access relies on the existing admin-route trust boundary

The browser does not maintain a separate session model. The frontend uses same-origin `fetch(...)` calls against the Flask admin routes in `ui/admin/src/lib/api/client.ts`.

## Production Packaging

- Source tree: `ui/admin/`
- Built assets: `ui/admin/dist/`
- Container runtime dist path: `/app/ui/admin/dist`
- Runtime override env var: `CHATMOCK_ADMIN_UI_DIST_DIR`

The Docker image builds the Vite app in a Node builder stage, copies the built `dist/` directory into the Python runtime image, and points Flask at that packaged dist path by default.

## Route Map

`ui/admin/src/router.tsx` defines the active operator routes:

- `/admin/ui` -> `CurrentStateRoute`
- `/admin/ui/edit-config` -> `EditConfigRoute`
- `/admin/ui/prompt-files` -> `PromptFilesRoute`
- `/admin/ui/settings` -> `SettingsRoute`

Shared chrome is provided by `AdminLayout`, which owns:

- the page title and status banner
- the operator nav for `Current State`, `Edit Config`, `Prompt Files`, and `Settings`
- the outlet shell for active route content

## Composition Root

`ui/admin/src/App.tsx` is the orchestration boundary for the SPA.

It owns:

- all TanStack Query reads for current profiles, instances, prompts, runtime validation, draft state, and instance previews
- all mutation hooks for profiles, instances, draft actions, runtime actions, and prompt file operations
- derived global operator state such as `busy`, `error`, `notice`, `statusText`
- the `AdminAppContext` provider consumed by route adapters
- the browser-local settings provider wiring from `ui/admin/src/lib/settings/*`

This means `App.tsx` is intentionally not a presentational component. It is the shared admin-control provider.

## Layer Boundaries

### 1. Router and layout

Files:

- `ui/admin/src/router.tsx`
- `ui/admin/src/layouts/AdminLayout.tsx`

Responsibilities:

- route definitions
- layout composition
- nav shell
- route outlet placement

Should not own:

- data fetching logic
- mutation side effects
- form validation rules

### 2. App provider

Files:

- `ui/admin/src/App.tsx`

Responsibilities:

- query orchestration
- mutation orchestration
- shared status derivation
- context wiring for route adapters

Should not own:

- large presentational markup for route pages
- field-level form rules
- styling primitives

### 3. Route adapters

Files:

- `ui/admin/src/routes/CurrentStateRoute.tsx`
- `ui/admin/src/routes/EditConfigRoute.tsx`
- `ui/admin/src/routes/PromptFilesRoute.tsx`

Responsibilities:

- read the shared admin context
- map context values/actions into feature-page props
- keep page-level feature boundaries simple

Should not own:

- direct `fetch` logic
- duplicated mutation setup
- shared shell logic

### 4. Query layer

Files:

- `ui/admin/src/lib/query-client.ts`
- `ui/admin/src/lib/query/*.ts`
- `ui/admin/src/lib/query/keys.ts`
- `ui/admin/src/lib/api/client.ts`
- `ui/admin/src/lib/query/shared.ts`

Responsibilities:

- API request execution
- cache keys
- query/mutation hooks
- normalization of error handling

Should not own:

- route structure
- page markup
- ad hoc local UI state

### 5. Feature pages

Files:

- `ui/admin/src/features/dashboard/DashboardPage.tsx`
- `ui/admin/src/features/edit-config/EditConfigPage.tsx`
- `ui/admin/src/features/profiles/ProfilesPage.tsx`
- `ui/admin/src/features/instances/InstancesPage.tsx`
- `ui/admin/src/features/prompt-files/PromptFilesPage.tsx`
- `ui/admin/src/features/settings/SettingsPage.tsx`
- `ui/admin/src/features/runtime-actions/RuntimeActionsPage.tsx`
- `ui/admin/src/features/draft-review/DraftReviewPage.tsx`

Responsibilities:

- render operator-facing screens
- compose local shared/UI components
- express page-specific interaction flows

Notes:

- `CurrentStateRoute` uses `DashboardPage` as the operator landing surface.
- `EditConfigPage` composes the structural editing subfeatures.
- `PromptFilesPage` owns immediate prompt-file editing and explicitly does not participate in draft/apply.
- `SettingsRoute` uses `SettingsPage` as the browser-local preferences surface.
- `SettingsPage` owns browser-local preferences only: applied theme and code-size settings, live preview, and `Apply` / `Reset` behavior.
- `BehaviorSettingsSection` and `AboutSettingsSection` are scaffold sections in the first pass and stay within the settings route boundary.
- `RuntimeActionsPage` and `DraftReviewPage` remain feature modules used inside larger route surfaces rather than top-level routes.

### 6. Browser-Local Settings Layer

Files:

- `ui/admin/src/lib/settings/types.ts`
- `ui/admin/src/lib/settings/theme-presets.ts`
- `ui/admin/src/lib/settings/storage.ts`
- `ui/admin/src/lib/settings/provider.tsx`

Responsibilities:

- define the browser-local settings shape, defaults, and storage key
- provide theme preset metadata and preview/apply/reset state
- apply the active theme to the document root and expose the live preview layer
- keep settings state isolated from backend config and runtime admin data

Should not own:

- server-backed preferences or admin API calls
- operator workflow routing beyond the settings route
- page-specific layout for other admin surfaces
### 7. Form adapters

Files:

- `ui/admin/src/forms/profileForm.ts`
- `ui/admin/src/forms/instanceForm.ts`

Responsibilities:

- typed translation between UI form input and registry/domain shapes
- field defaults and normalization rules used by structural editing flows

Should not own:

- network requests
- page layout

### 8. Local component layers

Primitive copied components:

- `ui/admin/src/components/ui/button.tsx`
- `ui/admin/src/components/ui/card.tsx`
- `ui/admin/src/components/ui/input.tsx`
- `ui/admin/src/components/ui/select.tsx`
- `ui/admin/src/components/ui/tabs.tsx`
- `ui/admin/src/components/ui/textarea.tsx`

ChatMock-specific shared wrappers:

- `ui/admin/src/components/shared/SurfaceCard.tsx`
- `ui/admin/src/components/shared/StatCard.tsx`

Rule:

- `components/ui/` is the owned primitive layer copied from shadcn-style sources.
- `components/shared/` is the ChatMock normalization layer for repeated usage patterns.
- Feature pages should prefer `components/shared/` for repeated operator patterns instead of inventing slightly different wrappers in each page.

## Data Contract Boundaries

Shared admin types live in:

- `ui/admin/src/lib/types/admin.ts`

These types describe the JSON contract expected from the Flask admin routes:

- `Profile`
- `Instance`
- `DraftState`
- `ValidationSummary`
- `InstancePreview`
- `DraftPreview`
- `PromptState`
- `PromptFilePayload`
- `RuntimeRedeployResponse`

If an admin endpoint payload changes, update `lib/types/admin.ts` and the relevant query hooks first, then update feature pages.

## Route To Endpoint Map

### Current State

Primary reads:

- `GET /admin/profiles`
- `GET /admin/instances`
- `GET /admin/draft`
- `GET /admin/prompts`
- `GET /admin/instances/<instance_id>/preview`
- `POST /admin/runtime/validate`

Primary actions:

- `POST /admin/prompts/reload`
- `POST /admin/draft/validate`
- `POST /admin/draft/preview`
- `POST /admin/draft/apply`
- `POST /admin/draft/reset`
- `POST /admin/runtime/redeploy`

### Edit Config

Primary reads:

- `GET /admin/draft`
- `GET /admin/profiles`
- `GET /admin/instances`

Primary actions:

- `POST /admin/profiles`
- `PUT /admin/profiles/<profile_id>`
- `DELETE /admin/profiles/<profile_id>`
- `POST /admin/instances`
- `PUT /admin/instances/<instance_id>`
- `DELETE /admin/instances/<instance_id>`

### Prompt Files

Primary reads:

- `GET /admin/prompts`
- `POST /admin/prompts/files/read`

Primary actions:

- `POST /admin/prompts/files/write`
- `POST /admin/prompts/reload`
- `POST /admin/prompts/config`

## Agent Documentation Strategy

For agents working in this UI, the best documentation surface is layered:

### Repo-local docs first

Use these for ChatMock-specific behavior:

- `docs/chatmock-admin-ui-architecture.md`
- `docs/chatmock-admin-ui-frontend-conventions.md`
- `docs/chatmock-instance-management.md`
- `DOCKER.md`

These explain the local route map, trust model, packaging, and feature ownership that upstream docs cannot know.

### Context7 for third-party libraries

Use Context7 for current external-library docs:

- React Router
- TanStack Query
- React Hook Form
- shadcn/ui

This is the right lane for API usage, version-specific behavior, and examples from those upstream projects.

### Repo code for copied components

For files under `ui/admin/src/components/ui/`, upstream shadcn docs are useful for origin patterns, but the local file contents are the actual source of truth because these components are copied into the repo and can drift from upstream.

## Recommended Maintenance Rule

When a future change adds one of these, update this doc in the same branch:

- a new top-level route
- a new shared context/provider
- a new component layer
- a new packaging/runtime path for the SPA
- a new global client-state tool

That keeps the UI boundary documentation from falling behind the code again.
