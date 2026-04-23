# ChatMock Browser Admin UI Operator-First Refresh

## Status

Proposed

## Date

2026-04-22

## Goal

Reshape the current browser admin UI into a simpler operator console that is easier to scan, easier to use on mobile, and clearer about which actions are immediate versus draft-based.

## Problem

The current UI works, but it asks the operator to hold too many concepts at once:

- five equal-weight navigation sections
- draft config editing and live prompt editing mixed too closely
- runtime actions separated from the current-state landing view
- dense metadata forms that expose low-signal fields at the same level as critical actions

The result is functional but harder to understand than it should be.

## User Decisions Captured

- Simplification should be operator-first
- The primary landing experience should be Current State
- The top-level visible actions should be:
  - Reload Prompts
  - Validate Runtime
  - Apply Draft when dirty
  - Redeploy
- Prompt file editing should remain on this branch and should be part of the redesigned flow
- The UI should be lightly stylized to feel cleaner and more intentional, not heavily redesigned

## Design Summary

Turn the app from a five-page admin surface into a three-mode operator console:

1. Current State
2. Edit Config
3. Prompt Files

Current State becomes the default landing page and the primary place where operators orient themselves and act. Config editing and prompt editing become clearly separated workspaces.

## Information Architecture

### Primary Navigation

Replace the current nav with three items:

- Current State
- Edit Config
- Prompt Files

These are not equal feature buckets. They reflect the operator’s actual workflow:

1. inspect live state
2. change config if needed
3. edit prompts if needed

### Current State

This becomes the home page and the main operational dashboard.

It should show:

- runtime validation result
- active prompt source
- current instances with labels, ports, and service names
- draft dirty state
- compact pending-change summary when the draft is dirty

It should provide the top-level action bar:

- Reload Prompts
- Validate Runtime
- Apply Draft only when the draft is dirty
- Redeploy

This page should make it obvious what is live now, what is pending, and which immediate actions are available.

### Edit Config

This page becomes a focused editor for YAML-backed structural state only.

Use a simple segmented switch or tab control inside the page:

- Profiles
- Instances

The default presentation should show only the fields operators are most likely to care about. Lower-signal fields stay available behind an Advanced disclosure.

Editing behavior remains the same:

- edits mutate the in-memory draft only
- nothing writes to YAML until Apply Draft

### Prompt Files

This page becomes the dedicated place for editing actual prompt content.

It should show:

- profile picker
- base prompt editor
- codex prompt editor
- prompt file paths
- Reload From Disk
- Save Prompt Files

Prompt file editing must be explicitly labeled as immediate file editing, not part of the structural draft/apply workflow.

## Interaction Model

### Current State Actions

- Reload Prompts:
  - immediate runtime action
  - reloads active prompt files into the prompt manager

- Validate Runtime:
  - immediate runtime check
  - validates current live registry-backed state

- Apply Draft:
  - visible only when the draft is dirty
  - writes YAML-backed profile and instance config
  - refreshes current-state data after success

- Redeploy:
  - immediate runtime action
  - still requires explicit confirmation

### Draft Visibility

Do not force the user to navigate to a dedicated draft-review page just to understand whether a draft exists.

Instead:

- show a draft dirty banner on Current State
- include a compact summary of pending draft profiles/instances
- provide a link or inline expansion for deeper draft preview details if needed

### Prompt Editing

Prompt editing should not be embedded in the same surface as config metadata editing.

This keeps the UI honest about the two different kinds of state:

- draft structural state
- immediate prompt file state

## Visual Direction

Keep the current visual language as a base, but reduce noise and improve hierarchy.

### Changes

- fewer card styles
- stronger visual emphasis on Current State
- less equal spacing between unrelated actions
- cleaner section headers
- softer surfaces with slightly warmer contrast
- more deliberate grouping of controls
- stronger distinction between:
  - primary actions
  - secondary actions
  - destructive actions

### Avoid

- a full visual rebrand
- adding decorative UI that competes with state visibility
- gradients or motion that make the console feel less operational

The aim is “cleaner and more legible,” not “flashier.”

## Mobile Behavior

The simplified structure should improve tailnet phone use:

- one primary landing page
- fewer navigation choices
- action bar near the top
- current state readable without scrolling through editing forms
- prompt editors and advanced fields isolated from the landing view

Edit Config and Prompt Files should stack cleanly on narrow screens, with Current State remaining the first and fastest page to understand.

## Implementation Outline

1. Collapse nav from five items to three
2. Rebuild Current State as the primary operator dashboard
3. Move draft-review concepts into Current State
4. Merge profile/instance structural editing under Edit Config
5. Move actual prompt editors into Prompt Files
6. Hide lower-signal config fields behind Advanced sections
7. Apply the lighter styling pass across shared layout primitives

## Constraints

- Keep the existing backend model:
  - draft config endpoints remain draft-based
  - prompt file editing remains immediate
  - runtime actions remain explicit
- Do not add a second auth model
- Do not change the local-only trust model
- Keep diffs focused on understandability and layout

## Success Criteria

- An operator can land on Current State and understand:
  - what is live
  - whether draft changes exist
  - what top-level actions are available
- Config editing no longer feels mixed with prompt editing
- Prompt editing is obvious and clearly immediate
- Mobile use requires fewer taps and less context switching
- The UI feels cleaner and more intentional without becoming visually noisy
