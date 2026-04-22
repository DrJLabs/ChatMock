# ChatMock Profile And Instance Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make prompt/profile management and multi-instance provisioning a first-class ChatMock capability that works cleanly for headless operations now and can later support a management UI without redesigning storage or runtime boundaries.

**Architecture:** Introduce a file-backed profile registry plus an instance registry, with explicit separation between immutable profile definitions and mutable instance/runtime state. Keep prompt content and instance wiring declarative so Docker Compose generation, host-process launchers, and future UI/API surfaces can all operate from the same source of truth.

**Tech Stack:** Python/Flask existing ChatMock app, YAML/JSON file-backed config, Docker Compose generation, optional host launcher scripts, future REST/WS admin surface

---

## File Structure

- `chatmock/profile_registry.py`
  - New loader/validator for prompt profiles and managed instances.
- `chatmock/instance_manager.py`
  - New orchestration helpers that materialize Compose/runtime definitions from registry state.
- `chatmock/admin_routes.py`
  - Future optional API surface for listing profiles, instances, and provisioning actions.
- `config/profiles/*.yaml`
  - Declarative prompt-profile definitions.
- `config/instances/*.yaml`
  - Declarative instance definitions referencing profiles plus port/runtime settings.
- `prompts/<profile-name>/prompt.md`
  - Profile-scoped base prompt content.
- `prompts/<profile-name>/prompt_gpt5_codex.md`
  - Profile-scoped Codex-family prompt content.
- `docker-compose.yml`
  - Generated or template-expanded managed runtime entrypoint for Docker deployments.
- `scripts/chatmock-instance`
  - Future CLI for `list`, `provision`, `render-compose`, `up`, `down`, `restart`, and `validate`.
- `tests/test_profile_registry.py`
  - Validation coverage for profile and instance schema loading.
- `tests/test_instance_manager.py`
  - Runtime/rendering coverage for Compose output and instance resolution.
- `docs/chatmock-instance-management.md`
  - Operator runbook for managed profiles and instances.

## Design Constraints

- Keep prompt content storage separate from runtime metadata.
- Shared auth/session state must remain opt-in and explicit per instance.
- Instances must reference profiles by stable ID, never by ad hoc host paths.
- Runtime generation must support Docker-first operations now without blocking future host/systemd support.
- UI compatibility stops at stable read/write contracts and lifecycle hooks; do not pre-build a UI-specific backend abstraction until operators need it.

## Proposed Config Model

### Prompt profile

Each profile should have:

- `id`
- `label`
- `description`
- `prompt_dir`
- `base_prompt_file`
- `codex_prompt_file`
- `model_overrides` (optional)
- `defaults` (optional per-profile env knobs such as `INJECT_DEFAULT_INSTRUCTIONS`)

Example shape:

```yaml
id: clawmem
label: ClawMem
description: Structured memory-enrichment prompt set
prompt_dir: prompts/clawmem
base_prompt_file: prompt.md
codex_prompt_file: prompt_gpt5_codex.md
defaults:
  CHATGPT_LOCAL_INJECT_DEFAULT_INSTRUCTIONS: true
```

### Managed instance

Each instance should have:

- `id`
- `label`
- `profile_id`
- `runtime` (`docker_compose` first; reserve `host_process` later)
- `bind_host`
- `port`
- `shared_home_group`
- `env_file`
- `extra_env`
- `healthcheck`
- `enabled`

Example shape:

```yaml
id: chatmock-clawmem
label: ChatMock ClawMem
profile_id: clawmem
runtime: docker_compose
bind_host: 127.0.0.1
port: 8001
shared_home_group: default
env_file: .env
extra_env: {}
healthcheck:
  path: /health
enabled: true
```

## Provisioning Model

Provisioning should be deterministic and file-backed:

1. Load profiles from `config/profiles/*.yaml`.
2. Load instances from `config/instances/*.yaml`.
3. Validate that every instance references a known profile and that required prompt files exist.
4. Resolve shared-home groups into concrete runtime mounts/paths.
5. Render runtime artifacts from registry state.
6. Apply lifecycle action (`up`, `down`, `restart`, `status`) through a single manager path.

This avoids embedding per-instance knowledge in Compose files or shell aliases.

## Compose / Runtime Integration

Recommended first implementation:

- Keep Docker Compose as the initial managed runtime backend.
- Generate a stable `docker-compose.generated.yml` from profile/instance definitions.
- Keep handwritten `docker-compose.yml` minimal:
  - either `include` the generated file if the toolchain supports it
  - or document `docker compose -f docker-compose.generated.yml ...` as the managed entrypoint

Generation rules:

- one service per enabled instance
- each service mounts prompt files from the selected profile
- each service resolves `CHATGPT_LOCAL_HOME` from `shared_home_group`
- each service gets stable container naming derived from instance ID
- each service gets explicit healthcheck and bind host/port

Future host runtime backend:

- add a second renderer for shell/systemd launch artifacts
- preserve the same profile/instance registries
- do not fork the config model

## Prompt / Profile Storage Rules

- Prompt files live under `prompts/<profile-id>/`
- Root-level prompt files become compatibility/default inputs only until migrated
- Profiles own prompt selection; instances never point directly at arbitrary prompt files
- Edits to prompt content should happen in profile directories, not in runtime manifests
- Validation must fail fast if a profile omits either prompt file

## UI-Readiness Boundaries

Build only the seams needed for future UI compatibility:

- stable profile and instance schemas
- deterministic validation errors
- list/read/create/update/delete lifecycle for profiles and instances
- render-preview endpoint/CLI output for Compose artifacts
- dry-run provisioning support

Do not build yet:

- browser UI components
- auth model for admin users
- live terminal/stream log viewer
- multi-user conflict handling

Those should wait until there is a concrete UI delivery project.

## Recommended Task Decomposition

This should be executed as multiple future tasks, not one oversized implementation:

1. **Registry foundation**
   - Add profile and instance schemas, loaders, validators, and tests.
   - Migrate current manually wired prompt directories into registry-backed definitions.

2. **Provisioning backend**
   - Add instance manager plus Compose renderer/launcher.
   - Make existing multi-instance deployment run from generated artifacts rather than ad hoc manual services.

3. **Operator surface**
   - Add CLI commands for validation, render preview, provision, and lifecycle management.
   - Add operator docs for prompt/profile editing and instance rollout.

4. **UI-ready admin contract**
   - Add minimal admin API endpoints for listing profiles/instances and previewing generated runtime state.
   - Stop here unless a real UI project is approved.

## Delivery Sequence

- Start with registry and validation.
- Then move runtime generation under manager control.
- Then add operator CLI.
- Only after those are stable, expose an API surface for future UI work.

## Risks And Guardrails

- **Prompt drift risk:** duplicated prompt content can diverge silently.
  - Guardrail: require profiles to own prompt files and expose a validation command that checks for missing or duplicate paths.
- **Runtime drift risk:** generated runtime artifacts can diverge from committed hand-edited files.
  - Guardrail: either commit generated artifacts or make generation part of the deployment command; do not support mixed manual edits.
- **State-collision risk:** multiple instances may unintentionally share auth/session state.
  - Guardrail: require explicit `shared_home_group` declarations and show them in render output.
- **UI overreach risk:** building API/UI abstractions too early can distort the simpler operator workflow.
  - Guardrail: limit initial admin surface to read/validate/render/provision primitives.

## Implementation Handoff Notes

- The current repo already has two manually declared services and profile-specific prompt directories in progress; use that as migration seed data, not as the final management model.
- Treat prompt/profile management as a repo-owned capability, not a user-global Codex concern.
- Keep future diffs minimal by migrating current manual wiring into registries before adding new runtime backends or UI affordances.
