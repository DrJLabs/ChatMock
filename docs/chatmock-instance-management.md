# ChatMock Instance Management

## Purpose

ChatMock now has a registry-backed management layer for prompt profiles and managed instances.

This layer now supports two distinct control lanes:

- current-state inspection and immediate runtime actions
- in-memory draft/apply structural edits for YAML-backed config

It still does **not** replace the live prompt manager or the live Docker Compose entrypoint.

## Source Of Truth

Profile definitions live in:

- `config/profiles/*.yaml`

Managed instance definitions live in:

- `config/instances/*.yaml`

Prompt content still lives in:

- `prompts/bare/`
- `prompts/clawmem/`

Live runtime prompt switching still flows through:

- `GET /admin/prompts`
- `POST /admin/prompts/reload`
- `POST /admin/prompts/config`

## What The Registries Control

Profiles define:

- label and description
- prompt directory
- base prompt file
- codex prompt file
- runtime defaults
- UI metadata

Instances define:

- which profile is attached
- bind host and port
- compose service name
- container name
- runtime prompt config path
- shared state group
- healthcheck metadata
- UI metadata

## Current Seed State

Profiles:

- `bare`
- `clawmem`

Instances:

- `chatmock`
- `chatmock-clawmem`

Both current instances are modeled as part of the same shared state group:

- `shared-auth-default`

That reflects the current `docker-compose.yml` behavior where both services share the same `/data` volume.

## CLI

Available inspection commands:

```bash
chatmock instances list
chatmock instances validate
chatmock instances preview chatmock
chatmock instances preview chatmock-clawmem
```

`chatmock instances list` prints one line per instance with bind target, profile, and state group.

`chatmock instances validate` reports whether the registry set is internally consistent.

`chatmock instances preview <instance_id>` prints the resolved runtime preview JSON for one instance.

## HTTP Admin Endpoints

The existing local-only admin guard also protects the registry-backed read/preview endpoints:

- `GET /admin/profiles`
- `GET /admin/instances`
- `GET /admin/instances/<instance_id>/preview`

Draft and runtime mutation endpoints are also available:

- `GET /admin/draft`
- `POST /admin/draft/reset`
- `POST /admin/draft/validate`
- `POST /admin/draft/preview`
- `POST /admin/draft/apply`
- `POST /admin/profiles`
- `PUT /admin/profiles/<profile_id>`
- `DELETE /admin/profiles/<profile_id>`
- `POST /admin/instances`
- `PUT /admin/instances/<instance_id>`
- `DELETE /admin/instances/<instance_id>`
- `POST /admin/runtime/validate`
- `POST /admin/runtime/prompts/reload`
- `POST /admin/runtime/redeploy`

These endpoints are intended to be reusable by:

- CLI
- local scripts
- the browser admin SPA
- any later automation that needs a stable JSON contract

The payloads are JSON-first so the UI does not need to re-derive backend state from terminal output.

## Runtime Relationship

The registry layer does not own live prompt reload behavior.

Responsibilities are split like this:

- registries define default managed state and previewable runtime intent
- `PromptManager` owns live prompt selection and cached prompt contents
- `docker-compose.yml` remains the live runtime entrypoint in this phase

## Browser Admin UI

The primary operator surface now lives at:

- `GET /admin/ui`

The SPA source lives under:

- `ui/admin/`

It uses:

- separate Vite dev mode during implementation
- Flask-served built assets in production
- the same local-only trust model as the admin API
- a single in-memory draft workspace for structural edits

Draft/apply semantics:

- structural profile and instance edits change only the draft
- validation and preview operate on the draft without writing YAML
- Apply writes the YAML-backed config and clears the dirty draft state
- redeploy remains a separate explicit runtime action

This keeps destructive or operational actions explicit instead of hiding them behind config writes.
