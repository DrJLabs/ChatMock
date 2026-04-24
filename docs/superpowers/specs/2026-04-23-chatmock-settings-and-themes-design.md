# ChatMock Settings And Themes

## Status

Proposed

## Date

2026-04-23

## Goal

Add a durable browser-local `Settings` surface to the ChatMock admin UI, starting with a dark-first `UI` settings section for theme presets and code/font size, while preserving the current operator workflow boundaries.

## Problem

The browser admin UI now has a strong operator workflow for:

- current live state
- structural config editing
- prompt file editing

But it does not yet have a place for browser-local preferences such as:

- visual theme selection
- readable editor/code text sizing
- future UI and behavior preferences

If these preferences are mixed into the existing operator routes, the current mental model gets weaker:

- `Current State` stops being primarily operational
- `Edit Config` becomes an awkward mix of YAML-backed config and browser-local preferences
- `Prompt Files` gains unrelated UI controls

The result would be a less honest information architecture even if the controls technically worked.

## User Decisions Captured

- `Settings` should become a top-level route because it is likely to expand over time.
- `Settings` should support nested sections, starting with `UI`.
- Theme preference should be browser-local so different devices can use different themes.
- The first iteration should include a visible theme switcher.
- The first iteration should also include code/font size control.
- Code/font size should affect code-heavy surfaces, not the entire UI shell.
- Theme and code/font size changes should preview immediately for easier comparison.
- Settings should still have explicit `Apply` and `Reset` actions.
- Dark themes should be favored.
- Initial section scaffolding should be real, even if only `UI` is fully functional.

## Design Summary

Add a fourth top-level route:

- `Current State`
- `Edit Config`
- `Prompt Files`
- `Settings`

`Settings` is not a replacement for the rest of the admin UI. It is a separate browser-preference surface.

Inside `Settings`, add section-level navigation:

- `UI`
- `Behavior`
- `About`

Only `UI` is fully functional in the first pass. `Behavior` and `About` ship as intentionally minimal sections that establish the long-term shape without pretending to own unfinished features.

## Information Architecture

### Top-Level Navigation

Keep the existing operator routes intact and add `Settings` as a peer route.

Reasoning:

- `Current State` remains the place to orient and act on runtime.
- `Edit Config` remains the place for draft-based structural changes.
- `Prompt Files` remains the place for immediate on-disk prompt edits.
- `Settings` becomes the place for browser-local and future cross-cutting preferences.

This keeps operational state and personal UI preferences separate.

### Settings Sections

#### UI

This section owns browser-local presentation preferences:

- active theme preset
- code/font size

This is the only fully implemented section in the first pass.

#### Behavior

This section is a scaffold for future browser-local preferences such as:

- confirmation behavior
- auto-refresh or polling preferences
- default landing page

In the first pass it should be visibly real but minimal, for example:

- brief description of intended future ownership
- clear “not configured yet” message

#### About

This section is a scaffold for low-risk informational settings and metadata such as:

- UI version/build context
- documentation links
- possibly active theme/debug information

In the first pass it should also be minimal and honest rather than decorative.

## What Should Not Move Into Settings

Do **not** move the following into `Settings`:

- structural profile editing
- structural instance editing
- draft validation/preview/apply
- prompt file editing
- runtime actions such as reload, validate, redeploy

Those remain operator workflows, not preferences.

The admin UI as a whole is “settings-like,” but not all settings are the same kind of state:

- YAML-backed structural config
- immediate runtime actions
- immediate prompt file edits
- browser-local presentation preferences

`Settings` should own only the fourth category in the first pass.

## Theme System

### Theming Model

Reuse the existing CSS-variable theme architecture in `ui/admin/src/styles.css`.

Do not introduce a second theming mechanism.

The intended pattern is:

- keep semantic CSS tokens such as `--background`, `--foreground`, `--primary`, and related sidebar/chart tokens
- define multiple preset token sets under theme selectors
- toggle the active theme on the document root with a stable theme marker such as a class or data attribute

This aligns with the current shadcn/Tailwind CSS-variable setup and avoids component-level rewrites.

### Preset Direction

Themes should be dark-first.

The first pass should ship a curated set of built-in presets with a strong bias toward dark surfaces and clear contrast. Examples of appropriate directions:

- graphite / obsidian
- blue-black / operator console
- muted slate / low-glare
- high-contrast dark

The exact names and palettes can be finalized during implementation, but the set should feel intentionally different rather than like tiny color tweaks.

### Source Of Truth

Theme presets live in repo-local CSS and UI settings metadata.

Upstream shadcn theming ideas can inform the preset design, but this repo remains the source of truth because the components are copied into the codebase and the theme tokens already have local meaning.

## Code/Font Size Setting

### Scope

The first-pass text-size setting should affect only technical-text surfaces, not the overall UI shell.

Included:

- prompt editor textareas
- `code` blocks
- preview/output blocks that render dense technical text

Excluded:

- page titles
- nav labels
- cards and general body copy
- global spacing and shell typography

### Control

Use a slider with bounded min/max values and sensible defaults.

The user asked specifically for a slider rather than discrete presets.

The slider should feel continuous enough for comparison without exposing absurd extremes.

## Preview / Apply / Reset Model

### Behavior

Both theme and code/font size should preview immediately when the user changes them inside `Settings > UI`.

However, those previewed values should remain unapplied until the user clicks `Apply`.

`Reset` should discard the current preview and restore the last applied settings.

### State Model

Maintain two layers of settings state:

- applied settings
- draft settings

Applied settings:

- loaded from local storage on app startup
- represent the committed browser-local preferences

Draft settings:

- exist while the user interacts with `Settings > UI`
- drive the live preview while the user experiments

Actions:

- changing controls updates draft settings immediately
- preview reads draft settings immediately
- `Apply` copies draft to applied and writes local storage
- `Reset` replaces draft with the currently applied values

### Persistence Boundary

Store only applied settings in local storage.

Do not write draft preview state to local storage until `Apply`.

This gives the user safe experimentation while preserving per-browser independence.

## Routing And Composition

### New Route

Add a new top-level route under the existing admin router:

- `/admin/ui/settings`

The top-level nav should expose `Settings` as a peer item next to the three current operator routes.

### Settings Page Composition

Use a page shell that supports internal section navigation.

First-pass internal sections:

- `UI`
- `Behavior`
- `About`

The section nav can be implemented as segmented controls, tabs, or a small sidebar, but it should clearly read as sub-navigation inside Settings rather than as a second top-level app nav.

### UI Section Composition

The `UI` section should contain:

- theme preset selector with strong visual preview affordance
- code/font size slider
- `Apply`
- `Reset`

Recommended layout:

- settings controls in the primary column
- compact preview or explanatory panel nearby if needed

The section should make it clear that changes preview locally before they are applied.

## UX Rules

### Theme Selection

Selecting a theme should immediately restyle the app for preview.

The control should make it easy to compare presets quickly.

The currently applied theme and currently previewed theme should be distinguishable when they differ.

### Code/Font Size

Changing the slider should immediately update prompt editors and code-like surfaces.

The user should not need to navigate away to confirm that the size changed.

### Reset

`Reset` should feel safe and predictable:

- discard preview-only changes
- restore the last applied theme
- restore the last applied code/font size

### Apply

`Apply` should make the current preview persistent for that browser/device only.

No backend mutation should occur.

## Constraints

- Keep theme persistence browser-local.
- Do not add backend settings endpoints.
- Do not add a second authentication/session model.
- Do not blur operator workflow routes with browser-local preferences.
- Preserve the existing route and backend trust model.
- Reuse the current CSS-variable token system instead of inventing a new theming stack.
- Keep first-pass scope focused on:
  - settings route
  - section shell
  - functional `UI` section
  - scaffolded `Behavior` and `About`

## Alternatives Considered

### Put UI preferences inside `Edit Config`

Rejected because `Edit Config` is explicitly about draft-based YAML-backed structural state. Browser-local theme and text-size preferences are a different class of state.

### Make theme changes persist immediately on selection

Rejected because the user wanted `Apply` and `Reset`, and those controls only make sense if preview state is distinct from applied state.

### Scale the entire UI with the font-size control

Rejected for the first pass because it would destabilize the overall shell hierarchy and spacing when the main need is technical-text readability.

### Make settings server-backed

Rejected for the first pass because it adds backend complexity and defeats the goal of letting different devices use different themes.

## Success Criteria

- `Settings` exists as a top-level route without weakening the current operator workflow routes.
- `Settings > UI` allows immediate preview of multiple dark-first theme presets.
- `Settings > UI` allows immediate preview of code/font size changes on technical-text surfaces.
- `Apply` persists only the current browser’s chosen values.
- `Reset` reliably restores the last applied values.
- `Behavior` and `About` exist as credible section scaffolds without pretending to be complete.
- The resulting structure leaves clear room for future browser-local preferences without turning the whole app into one undifferentiated settings surface.

## Implementation Notes For The Next Phase

The following should be made explicit in the implementation plan:

- exact route/file changes for adding `Settings`
- exact local-storage key shape
- exact draft/applied settings model
- exact document-root theme application method
- exact list of surfaces affected by code/font size
- test coverage for:
  - route rendering
  - preview behavior
  - apply/reset behavior
  - local-storage persistence
