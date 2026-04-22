# ChatMock Live Prompt Reload Design

**Date:** 2026-04-22

**Goal**

Allow the running ChatMock process to switch prompt directories and reload prompt content through a local-only HTTP admin API, without restarting the container or process.

## Problem

ChatMock currently loads `prompt.md` and `prompt_gpt5_codex.md` once at import time in `chatmock/config.py`, then stores the contents in module globals. The Docker split between `prompts/bare/` and `prompts/clawmem/` is implemented by bind mounts in `docker-compose.yml`, so changing the active prompt set requires editing compose and recreating containers.

That is operationally heavier than necessary and makes prompt switching a deployment action instead of a runtime action.

## Recommended Approach

Implement a file-backed prompt runtime config plus an explicit local admin HTTP API.

### Why this approach

- It supports true live prompt path changes without container restarts.
- It keeps the source of truth on disk instead of hiding it in process memory.
- It avoids per-request file I/O by keeping prompts cached until an explicit reload.
- It keeps the runtime surface narrow and auditable.

## Scope

### In scope

- Add a prompt manager that owns:
  - active prompt directory or explicit file paths
  - cached prompt contents
  - reload logic
- Add a small runtime config file for prompt path selection.
- Add local-only admin endpoints to:
  - inspect current prompt config
  - update prompt config
  - reload prompt cache
- Update instruction selection to read prompt contents from the prompt manager rather than startup-time globals.
- Add focused tests for reload and config mutation behavior.

### Out of scope

- Multi-user auth or broad remote administration.
- Automatic file-watch reload.
- Non-HTTP control surfaces such as signals.
- Redesign of prompt semantics or instruction-selection policy.

## Architecture

### 1. Prompt manager

Create a small prompt manager in `chatmock/config.py` or a nearby dedicated module.

Responsibilities:

- Resolve the active prompt file locations.
- Load `prompt.md` and `prompt_gpt5_codex.md`.
- Cache the loaded text in memory.
- Expose read methods used by request handling.
- Expose `reload()` and `update_config(...)` methods.
- Persist prompt-path selection to a small runtime config file.

Suggested shape:

- `PromptConfig`
  - `prompt_dir`
  - `base_prompt_path`
  - `codex_prompt_path`
- `PromptManager`
  - `get_instructions(model, use_codex_variant)`
  - `get_state()`
  - `reload()`
  - `update_config(...)`

### 2. File-backed runtime config

Use a small JSON file under the app’s writable state directory so runtime prompt selection survives restart.

Suggested location:

- `${CHATGPT_LOCAL_HOME}/prompt-config.json`

Suggested contents:

```json
{
  "prompt_dir": "/app/prompts/bare",
  "base_prompt_path": "/app/prompts/bare/prompt.md",
  "codex_prompt_path": "/app/prompts/bare/prompt_gpt5_codex.md"
}
```

Rules:

- If `base_prompt_path` and `codex_prompt_path` are not provided, derive them from `prompt_dir`.
- If no runtime config file exists, initialize from env defaults and current behavior.
- Validate that target files exist and are readable before accepting an update.

### 3. Admin HTTP API

Add a local-only admin surface in `chatmock/app.py`.

Endpoints:

- `GET /admin/prompts`
  - Returns current runtime prompt config and metadata about the loaded cache.
- `POST /admin/prompts/config`
  - Updates the runtime config on disk and reloads prompt cache.
- `POST /admin/prompts/reload`
  - Reloads prompt cache from the current runtime config without changing config.

Suggested response fields:

- `prompt_dir`
- `base_prompt_path`
- `codex_prompt_path`
- `loaded_at`
- `source`

### 4. Local-only guardrail

The admin API must not be generally exposed.

Guardrails:

- Accept requests only from loopback (`127.0.0.1`, `::1`) or equivalent proxied-local cases if clearly identified.
- Optionally require a static header token if `CHATMOCK_ADMIN_TOKEN` is configured.
- Return `403` for non-local callers.

### 5. Request-path integration

Update instruction selection so request handlers do not use startup-loaded module globals.

Instead:

- `create_app()` initializes one prompt manager instance.
- Store it on `app.extensions` or `app.config`.
- `resolve_effective_instructions(...)` reads current prompt text from the manager each request, but only from the in-memory cache.

This keeps request behavior stable while allowing explicit runtime reloads.

## Docker implications

The runtime prompt switch should stop requiring compose edits.

Preferred Docker shape:

- mount a stable prompts root into the container, such as:
  - `/app/prompts/bare/...`
  - `/app/prompts/clawmem/...`
- keep the running app pointed at one active prompt directory via runtime config.

That means future prompt switching can use the admin API to move between mounted prompt directories rather than changing bind mounts.

## Failure handling

- If a config update points to missing or unreadable files, reject the request with `400`.
- If reload fails, keep the previous cached prompts active.
- Surface structured error messages so operators can see exactly which file failed validation.

## Testing

Add focused tests for:

- prompt manager loads defaults from current startup behavior
- reload updates cache after on-disk file change
- config update switches between two prompt directories
- invalid path update is rejected and prior cache remains active
- admin endpoints are local-only
- instruction resolution uses the prompt manager cache instead of module globals

## Operational workflow after change

Example live switch:

1. `POST /admin/prompts/config` with `{"prompt_dir":"/app/prompts/clawmem"}`
2. server validates files and rewrites runtime config
3. server reloads prompt cache
4. subsequent requests use ClawMem prompts immediately

Example manual refresh after editing prompt files:

1. edit files in the mounted prompt directory
2. `POST /admin/prompts/reload`
3. new requests use refreshed prompt text

## Tradeoffs

### Advantages

- no container restart for prompt switching
- explicit and auditable control path
- deterministic persisted state
- no per-request file reads

### Costs

- introduces a new admin surface that must be guarded
- adds mutable runtime config state
- requires refactoring prompt loading away from startup globals

## Implementation notes

- Keep the first version JSON-only for the runtime config.
- Keep endpoint behavior narrow and explicit; no generic config mutation API.
- Keep the existing prompt file names (`prompt.md`, `prompt_gpt5_codex.md`) so current prompt sets remain compatible.
