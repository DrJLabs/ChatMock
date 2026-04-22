# ChatMock Instance Management

## Purpose

ChatMock now has a registry-backed management layer for prompt profiles and managed instances.

This layer is intentionally limited to:

- inspect
- validate
- preview

It does **not** replace the live prompt manager or the live Docker Compose entrypoint in this phase.

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

These endpoints are intended to be reusable by:

- CLI
- local scripts
- the current PySide GUI
- a future replacement GUI

The payloads are JSON-first so UI work does not need to re-derive backend state from terminal output.

## Runtime Relationship

The registry layer does not own live prompt reload behavior.

Responsibilities are split like this:

- registries define default managed state and previewable runtime intent
- `PromptManager` owns live prompt selection and cached prompt contents
- `docker-compose.yml` remains the live runtime entrypoint in this phase

## Next Phase

The next decision point is whether the current `gui.py` should be adapted to consume the new management layer or whether a replacement GUI should be built.

Because the service and admin responses are now JSON-first, either path can reuse the same management contract without redesigning the backend again.
