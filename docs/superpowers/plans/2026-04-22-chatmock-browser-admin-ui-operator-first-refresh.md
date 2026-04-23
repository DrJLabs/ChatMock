# ChatMock Browser Admin UI Operator-First Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the browser admin UI into an operator-first console with `Current State`, `Edit Config`, and `Prompt Files` as the primary modes.

**Architecture:** Keep the existing backend contracts intact and reshape the React UI around three top-level workspaces. Move draft visibility into the landing page, keep structural edits draft-based, and keep prompt file edits immediate but clearly separated.

**Tech Stack:** React, Vite, TypeScript, existing Flask admin JSON endpoints, CSS

---

## File Structure

- Modify: `ui/admin/src/App.tsx`
  - Collapse the nav, manage the three-mode shell, and route current/draft/prompt data to the right pages.
- Modify: `ui/admin/src/features/dashboard/DashboardPage.tsx`
  - Rebuild as the main Current State operator dashboard with top-level actions and draft visibility.
- Modify: `ui/admin/src/features/profiles/ProfilesPage.tsx`
  - Narrow the page to structural profile editing only and hide lower-signal details.
- Modify: `ui/admin/src/features/instances/InstancesPage.tsx`
  - Narrow the page to structural instance editing only and hide lower-signal details.
- Create: `ui/admin/src/features/edit-config/EditConfigPage.tsx`
  - Host the segmented `Profiles` / `Instances` config-edit workspace.
- Create: `ui/admin/src/features/prompt-files/PromptFilesPage.tsx`
  - Host prompt-file editing with profile selection and immediate save/reload controls.
- Modify: `ui/admin/src/styles.css`
  - Lightly restyle shared layout primitives to make hierarchy calmer and clearer.

## Task 1: Lock the three-mode shell

**Files:**
- Modify: `ui/admin/src/App.tsx`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Replace the five-item nav with the three-mode nav**

Change the page keys to:

```ts
type PageKey = "current-state" | "edit-config" | "prompt-files";

const NAV_ITEMS: Array<{ key: PageKey; label: string }> = [
  { key: "current-state", label: "Current State" },
  { key: "edit-config", label: "Edit Config" },
  { key: "prompt-files", label: "Prompt Files" },
];
```

- [ ] **Step 2: Make `current-state` the default hash route**

Update the route reader so any unknown or empty hash lands on `current-state`.

- [ ] **Step 3: Run the build after the shell route change**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 2: Make Current State the real landing page

**Files:**
- Modify: `ui/admin/src/features/dashboard/DashboardPage.tsx`
- Modify: `ui/admin/src/App.tsx`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Replace dashboard copy and layout with operator-state framing**

The page should emphasize:

- runtime validation
- active prompt source
- current instance list
- draft dirty state
- compact pending-change summary

- [ ] **Step 2: Surface the top-level action bar on the landing page**

Expose:

- `Reload Prompts`
- `Validate Runtime`
- `Apply Draft` only when dirty
- `Redeploy`

Wire them to the existing callbacks already in `App.tsx`.

- [ ] **Step 3: Move draft visibility into Current State**

Add a compact draft banner/card that shows:

- whether the draft is dirty
- draft profile count
- draft instance count
- a short note that structural edits remain unapplied until Apply

- [ ] **Step 4: Rebuild after the landing-page refresh**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 3: Merge structural config editing under one workspace

**Files:**
- Create: `ui/admin/src/features/edit-config/EditConfigPage.tsx`
- Modify: `ui/admin/src/features/profiles/ProfilesPage.tsx`
- Modify: `ui/admin/src/features/instances/InstancesPage.tsx`
- Modify: `ui/admin/src/App.tsx`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Create the `EditConfigPage` wrapper**

Build a page that renders a segmented switch between:

- `Profiles`
- `Instances`

and mounts the existing editor components under that switch.

- [ ] **Step 2: Simplify the profile editor**

Keep the common fields visible:

- id
- label
- description
- prompt directory
- base prompt path
- codex prompt path

Move lower-signal fields into an `Advanced` section:

- UI order
- `inject_default_instructions`
- `editable`

- [ ] **Step 3: Simplify the instance editor**

Keep the common fields visible:

- id
- label
- profile
- port
- bind host
- prompt config path
- enabled

Move lower-signal fields into an `Advanced` section:

- state group
- compose service
- container name
- env prefix
- healthcheck path
- mutable fields
- UI order
- runtime display

- [ ] **Step 4: Mount `EditConfigPage` from the app shell**

Use the existing profile/instance callbacks; do not change backend behavior.

- [ ] **Step 5: Rebuild after the config-workspace merge**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 4: Separate prompt editing into its own page

**Files:**
- Create: `ui/admin/src/features/prompt-files/PromptFilesPage.tsx`
- Modify: `ui/admin/src/App.tsx`
- Modify: `ui/admin/src/features/profiles/ProfilesPage.tsx`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Create the `PromptFilesPage`**

This page should include:

- profile picker
- prompt file paths
- base prompt textarea
- codex prompt textarea
- `Reload From Disk`
- `Save Prompt Files`

- [ ] **Step 2: Move prompt editing out of `ProfilesPage`**

Remove the prompt text editor block from the profile-structure page so prompt-file editing is no longer mixed with YAML-backed config editing.

- [ ] **Step 3: Keep prompt editing immediate**

Reuse the existing `loadPromptFiles` and `savePromptFiles` callbacks from `App.tsx`. Do not add draft semantics to prompt file saving.

- [ ] **Step 4: Rebuild after prompt-page extraction**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 5: Lightly restyle the shared shell

**Files:**
- Modify: `ui/admin/src/styles.css`
- Test: `cd ui/admin && npm run build`

- [ ] **Step 1: Reduce visual noise in the shell**

Update the shared styles so:

- the topbar feels lighter
- Current State gets clearer hierarchy
- cards feel more uniform
- action groups read more clearly

- [ ] **Step 2: Keep the redesign restrained**

Do not add new animation systems or heavy branding. Focus on:

- calmer spacing
- clearer grouping
- softer surfaces
- more obvious primary/secondary/destructive action distinctions

- [ ] **Step 3: Rebuild after the style pass**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

## Task 6: Final verification

**Files:**
- Test: `ui/admin`

- [ ] **Step 1: Run the frontend build**

Run:

```bash
cd ui/admin && npm run build
```

Expected: PASS

- [ ] **Step 2: Run the backend regression suite that protects the admin/UI lane**

Run:

```bash
/home/drj/tools/chatmock/.venv/bin/python -m pytest tests/test_admin_routes.py tests/test_admin_draft_service.py tests/test_profile_registry.py tests/test_instance_registry.py tests/test_instance_service.py tests/test_routes.py tests/test_cli.py -q
```

Expected: PASS

- [ ] **Step 3: Review the final UI diff**

Run:

```bash
git diff -- ui/admin docs/superpowers/specs/2026-04-22-chatmock-browser-admin-ui-operator-first-refresh-design.md docs/superpowers/plans/2026-04-22-chatmock-browser-admin-ui-operator-first-refresh.md
```

Expected: The diff should show the shell collapse to three modes, the landing-page operator focus, the config/prompt separation, and the light style cleanup.
