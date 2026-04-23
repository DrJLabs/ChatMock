# ChatMock Admin UI Stack Evaluation

## Date

2026-04-23

## Scope

Evaluate the proposed stack for the growing ChatMock admin UI:

- React Router v7
- Vite
- Tailwind CSS v4
- shadcn/ui
- TanStack Query
- Zustand
- React Hook Form

The goal is to decide whether this stack makes sense for the current admin UI, what future complexity it introduces, and how it should be adopted if chosen.

## Current Admin UI Baseline

The admin UI in this worktree is currently:

- React + Vite + TypeScript
- custom CSS
- route switching via URL hash
- backend access through handwritten `fetch` helpers
- page-level and app-level state stored with `useState`
- no dedicated router, server-state library, form library, or shared component system

That means the UI is still early enough that stack changes are possible without a painful rewrite, but mature enough that unnecessary abstractions will become real maintenance cost.

## Executive Summary

This proposed stack is **mostly a good fit**, but only with clear boundaries.

Recommended:

- React Router v7
- Vite
- Tailwind CSS v4
- shadcn/ui
- TanStack Query
- React Hook Form

Conditionally recommended:

- Zustand, but only for narrow UI-only client state

The stack makes sense if the admin UI will continue growing into a longer-lived operator console. It will likely reduce future frontend chaos **if responsibilities are kept separate**.

The stack will increase future complexity if used indiscriminately, especially if:

- React Router data APIs and TanStack Query are both used as primary data-loading layers
- Zustand is allowed to hold server state or form state
- shadcn/ui components are copied into the codebase without local conventions

## Per-Library Evaluation

### 1. React Router v7

**Fit:** Good, with an important caveat

What it solves for this repo:

- real URL routing instead of hash routing
- nested layouts
- clearer separation between `Current State`, `Edit Config`, and `Prompt Files`
- better navigation state and link semantics

What the official docs say:

- React Router v7 supports three modes: Declarative, Data, and Framework
- the features are additive across those modes
- Framework mode adds the most architecture and Vite-plugin-driven behavior
- Declarative mode is the simplest choice when you mainly want routing
- Data mode adds loaders, actions, pending states, and related APIs

Source:

- React Router modes: <https://reactrouter.com/start/modes>
- Upgrade guide: <https://reactrouter.com/upgrading/v6>

Important caution for ChatMock:

This admin UI already has Flask as the backend and Vite as the client build tool. React Router Framework mode would be a larger architectural shift than is necessary for the current app. It is not the same as “just adding routing.”

**Recommendation:**

- adopt React Router v7
- use **Declarative mode** first
- consider **Data mode** later only if route-level loading/actions become clearly valuable
- avoid Framework mode for now

### 2. Vite

**Fit:** Already correct

What it solves:

- fast dev server
- straightforward SPA bundling
- clean static output for Flask to serve

No change needed here.

**Recommendation:**

- keep Vite

### 3. Tailwind CSS v4

**Fit:** Strong

What it solves:

- faster styling iteration
- easier responsive behavior
- easier dark mode
- stronger consistency in spacing, typography, colors, and layout tokens
- reduced growth of custom CSS complexity over time

What the official docs say:

- Tailwind v4 moved to CSS-first configuration
- design tokens can be expressed as CSS theme variables
- many utilities and variants are simplified in v4

Source:

- Tailwind v4 announcement: <https://tailwindcss.com/blog/tailwindcss-v4>

Why it fits ChatMock:

The current admin UI is still using a hand-maintained shared stylesheet. That is manageable now, but as more screens, components, and themes are added, a utility/token system becomes more valuable.

**Recommendation:**

- adopt Tailwind CSS v4

### 4. shadcn/ui

**Fit:** Good if Tailwind is adopted

What it solves:

- fast access to production-style component primitives
- accessible-ish baseline patterns for common controls
- good ecosystem fit for admin UIs
- straightforward styling and theming when used with Tailwind

What the official docs say:

- shadcn/ui supports Vite and React Router project templates
- it is intended to scaffold code into your app rather than hide components behind a dependency boundary

Source:

- Installation docs: <https://ui.shadcn.com/docs/installation>

Important tradeoff:

shadcn/ui gives you component code inside your repo. That is powerful because you own the components, but it also means long-term maintenance is your problem. This is a better fit when you expect to customize the UI heavily, which is true for ChatMock.

**Recommendation:**

- adopt shadcn/ui if Tailwind is adopted
- create local component conventions early so copied components do not drift into inconsistency

### 5. TanStack Query

**Fit:** Strong

What it solves:

- query caching
- mutation lifecycle handling
- invalidation after changes
- background refetching
- loading/error state consistency
- reduced manual fetch orchestration

What the official docs say:

- TanStack Query is focused on the problems of server state
- it is explicitly positioned as a solution for async/server data rather than generic client state

Source:

- TanStack Query overview: <https://tanstack.com/query/latest/docs/framework/react/overview>

Why it fits ChatMock:

This admin UI already has multiple server-state surfaces:

- current profiles
- current instances
- prompt state
- draft state
- draft previews
- runtime validation
- prompt file read/write mutations

Today those flows are managed by manual `fetch` orchestration. TanStack Query is a strong fit for exactly this class of UI.

**Recommendation:**

- adopt TanStack Query
- use it as the primary server-state layer

### 6. Zustand

**Fit:** Optional and narrow

What it solves:

- tiny, low-friction client-side state
- no-provider global UI state when appropriate
- useful for theme choice, current view preferences, drawers, filters, temporary UI state

What the official docs say:

- Zustand is intentionally small, fast, and hook-based
- it is not opinionated, but explicit

Source:

- Zustand introduction: <https://zustand.docs.pmnd.rs/getting-started/introduction>

Why it can become a problem:

Zustand is the most likely library in this stack to be overused. If it begins to hold:

- fetched server state
- mutation state
- form state

then it becomes an unnecessary second architecture layered on top of TanStack Query and React Hook Form.

**Recommendation:**

- do not treat Zustand as a foundation of the stack
- add it only when a specific UI-only state problem appears
- keep it small and local in scope

### 7. React Hook Form

**Fit:** Strong

What it solves:

- form state management
- validation plumbing
- fewer rerenders
- easier handling of large structural forms

What the official docs say:

- React Hook Form emphasizes performance and reduced rerenders
- shadcn/ui documents React Hook Form as a first-class integration path for forms

Source:

- React Hook Form home/docs: <https://www.react-hook-form.com/>
- shadcn/ui React Hook Form guide: <https://ui.shadcn.com/docs/forms/react-hook-form>

Why it fits ChatMock:

The admin UI already has structural editors for profiles and instances, and those forms will become more complex as the UI grows.

**Recommendation:**

- adopt React Hook Form for structural forms

## Where Future Complexity Comes From

The main risk is not that these libraries are individually too heavy. The risk is **overlap**.

### Bad future state

Future complexity will increase if the codebase ends up using:

- React Router loaders/actions for some data
- TanStack Query for other data
- Zustand for fetched data
- React Hook Form plus mirrored Zustand form state
- shadcn/ui components with no local conventions

That leads to multiple competing answers to the same questions:

- where is this data loaded?
- who owns mutation state?
- who owns pending/error state?
- what is local UI state vs server state vs form state?

### Good future state

Future complexity stays reasonable if each tool has a narrow job:

- **React Router:** URL routing and layout composition
- **TanStack Query:** server state
- **React Hook Form:** form state
- **Zustand:** small UI-only state
- **Tailwind + shadcn/ui:** styling and components

This is the key to making the stack scale cleanly.

## Recommended Stack Decision

### Adopt now

- React Router v7, Declarative mode
- Tailwind CSS v4
- shadcn/ui
- TanStack Query
- React Hook Form

### Keep as-is

- Vite

### Defer until justified

- Zustand

## Recommended Adoption Order

### Phase 1: UI foundation

Adopt:

- Tailwind CSS v4
- shadcn/ui
- React Router v7 (Declarative mode)

Why first:

- unlocks better structure and better component primitives
- does not yet force server-state or form architecture decisions

### Phase 2: data layer

Adopt:

- TanStack Query

Why second:

- cleanly replaces ad hoc fetch lifecycle code
- gives stable patterns for queries, mutations, and invalidation

### Phase 3: forms

Adopt:

- React Hook Form

Why third:

- once routing and component primitives settle, form conversion becomes clearer
- especially useful for the profile/instance editors

### Phase 4: optional UI state

Adopt only if needed:

- Zustand

Use for:

- theme selection
- drawer state
- minor UI preferences
- view-level client state that does not belong in the URL or server cache

## Rules Of Use

If this stack is adopted, these rules should be treated as policy:

1. React Router is for routes and layout, not the primary server-state engine.
2. TanStack Query owns backend data fetching, caching, and mutations.
3. React Hook Form owns form state.
4. Zustand must not hold fetched backend resources or duplicate form state.
5. shadcn/ui components should be wrapped or normalized through local conventions where needed.
6. Tailwind tokens and theme conventions should be documented early to avoid visual drift.

## Final Recommendation

This stack **does make sense** for the ChatMock admin UI, but only in a disciplined form.

The best version of the proposal is:

- React Router v7
- Vite
- Tailwind CSS v4
- shadcn/ui
- TanStack Query
- React Hook Form
- Zustand only when a specific UI-only state need appears

That combination is coherent and likely to improve long-term maintainability for a growing admin UI.

The risky version is adopting all of them at once without clear boundaries, especially if React Router data loading, TanStack Query, and Zustand all compete to own state.

## Sources

- React Router modes: <https://reactrouter.com/start/modes>
- React Router v6 to v7 upgrade guide: <https://reactrouter.com/upgrading/v6>
- Tailwind CSS v4 announcement: <https://tailwindcss.com/blog/tailwindcss-v4>
- shadcn/ui installation docs: <https://ui.shadcn.com/docs/installation>
- shadcn/ui React Hook Form guide: <https://ui.shadcn.com/docs/forms/react-hook-form>
- TanStack Query overview: <https://tanstack.com/query/latest/docs/framework/react/overview>
- Zustand introduction: <https://zustand.docs.pmnd.rs/getting-started/introduction>
- React Hook Form docs/home: <https://www.react-hook-form.com/>
