# ChatMock Profile And Instance Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a registry-backed profile and instance management layer on top of the current `dev` branch so ChatMock can validate, inspect, preview, and eventually provision managed instances without breaking the existing live prompt controls.

**Architecture:** Treat the current prompt manager, prompt directories, and per-service runtime prompt config files as the stable runtime substrate. Build a pure-Python management service above that substrate which owns profile and instance registries, compose preview/render logic, and JSON-serializable view models that can be consumed equally by CLI commands, Flask admin routes, and the existing PySide GUI.

**Tech Stack:** Python, Flask, PySide6 GUI consumer, YAML + JSON file-backed config, Docker Compose, unittest/pytest

---

## Current Baseline On `dev`

This plan assumes the following already exists on the branch you will implement from:

- `chatmock/config.py` already exposes `PromptManager` and `PromptConfigState`.
- `chatmock/app.py` already exposes:
  - `GET /admin/prompts`
  - `POST /admin/prompts/reload`
  - `POST /admin/prompts/config`
- `docker-compose.yml` already runs two managed services:
  - `chatmock`
  - `chatmock-clawmem`
- Prompt content already lives in profile-style directories:
  - `prompts/bare/`
  - `prompts/clawmem/`
- Each service already has its own runtime prompt config file via env:
  - `CHATMOCK_PROMPT_CONFIG`
  - `CHATMOCK_CLAWMEM_PROMPT_CONFIG`
- The current desktop GUI is `gui.py`, which launches a local ChatMock server process and is the first likely consumer for future instance controls.

This means the implementation must **not** re-solve live prompt switching or re-introduce direct prompt-file wiring as the primary control model.

## File Structure

- Modify: `pyproject.toml`
  - Add the YAML parser dependency used by the registries.
- Create: `chatmock/profile_registry.py`
  - Loads and validates declarative prompt-profile definitions.
- Create: `chatmock/instance_registry.py`
  - Loads and validates declarative managed-instance definitions.
- Create: `chatmock/instance_service.py`
  - Pure service layer for listing profiles/instances, validating state, computing previews, and producing UI/API-safe DTOs.
- Modify: `chatmock/app.py`
  - Add thin admin endpoints for profile/instance inspection and preview, backed by `instance_service`.
- Modify: `chatmock/cli.py`
  - Add operator commands that call the same service layer instead of duplicating logic.
- Create: `config/profiles/bare.yaml`
  - Canonical profile definition for the existing bare prompt set.
- Create: `config/profiles/clawmem.yaml`
  - Canonical profile definition for the existing ClawMem prompt set.
- Create: `config/instances/chatmock.yaml`
  - Canonical instance definition for the main service on port `8000`.
- Create: `config/instances/chatmock-clawmem.yaml`
  - Canonical instance definition for the ClawMem service on port `8001`.
- Modify: `docker-compose.yml`
  - Keep as the live runtime entrypoint, but make it easier to verify against registry-derived previews.
- Create: `tests/test_profile_registry.py`
  - Validation coverage for profile definitions.
- Create: `tests/test_instance_registry.py`
  - Validation coverage for instance definitions.
- Create: `tests/test_instance_service.py`
  - Preview/render/view-model coverage for the new management layer.
- Modify: `tests/test_routes.py`
  - Add route coverage for the new read/preview admin endpoints.
- Modify: `DOCKER.md`
  - Document registry-backed management and how it relates to current prompt admin controls.
- Create: `docs/chatmock-instance-management.md`
  - Operator runbook for profile edits, instance edits, preview, validation, and future GUI handoff.

## Design Constraints

- Keep `PromptManager` as the runtime owner of live prompt selection and cached prompt text.
- Profiles must reference stable prompt directories under `prompts/<profile-id>/`.
- Instances must reference profiles by stable `profile_id`, never by arbitrary prompt path strings.
- The first implementation phase must be **read/validate/preview first**, not destructive provisioning first.
- All management results must be exposed as JSON-serializable dictionaries/lists so the same service layer can back:
  - CLI
  - Flask admin routes
  - the current PySide GUI in `gui.py`
  - a future replacement GUI if `gui.py` is discarded
- Keep Docker Compose as the live runtime entrypoint until registry-driven previews prove parity with the hand-authored file.
- Do not force a generated `docker-compose.yml` in the first phase.
- Preserve the existing env contract wherever possible:
  - `CHATMOCK_PROMPT_DIR`
  - `CHATMOCK_PROMPT_CONFIG`
  - `CHATMOCK_CLAWMEM_PROMPT_DIR`
  - `CHATMOCK_CLAWMEM_PROMPT_CONFIG`
- Make shared auth/state explicit. The current shared `/data` volume should become declared state policy, not an accidental side effect.

## Proposed Config Model

### Prompt profile

Each profile should declare:

- `id`
- `label`
- `description`
- `prompt_dir`
- `base_prompt_file`
- `codex_prompt_file`
- `runtime_defaults`
- `ui`

Example:

```yaml
id: bare
label: Bare
description: Default low-opinion prompt set for the main ChatMock service
prompt_dir: prompts/bare
base_prompt_file: prompt.md
codex_prompt_file: prompt_gpt5_codex.md
runtime_defaults:
  inject_default_instructions: true
ui:
  order: 10
  editable: true
```

Exact file for `config/profiles/bare.yaml`:

```yaml
id: bare
label: Bare
description: Default low-opinion prompt set for the main ChatMock service
prompt_dir: prompts/bare
base_prompt_file: prompt.md
codex_prompt_file: prompt_gpt5_codex.md
runtime_defaults:
  inject_default_instructions: true
ui:
  order: 10
  editable: true
```

Exact file for `config/profiles/clawmem.yaml`:

```yaml
id: clawmem
label: ClawMem
description: ClawMem-specific prompt set for the secondary managed service
prompt_dir: prompts/clawmem
base_prompt_file: prompt.md
codex_prompt_file: prompt_gpt5_codex.md
runtime_defaults:
  inject_default_instructions: true
ui:
  order: 20
  editable: true
```

### Managed instance

Each instance should declare:

- `id`
- `label`
- `profile_id`
- `bind_host`
- `port`
- `runtime`
- `prompt_config_path`
- `state_group`
- `compose_service_name`
- `container_name`
- `env_overrides`
- `healthcheck`
- `ui`
- `enabled`

Example:

```yaml
id: chatmock
label: ChatMock
profile_id: bare
bind_host: 127.0.0.1
port: 8000
runtime: docker_compose
prompt_config_path: /data/prompt-config-chatmock.json
state_group: shared-auth-default
compose_service_name: chatmock
container_name: chatmock
env_overrides: {}
healthcheck:
  path: /health
ui:
  order: 10
  mutable_fields:
    - profile_id
    - port
enabled: true
```

Exact file for `config/instances/chatmock.yaml`:

```yaml
id: chatmock
label: ChatMock
profile_id: bare
bind_host: 127.0.0.1
port: 8000
runtime: docker_compose
prompt_config_path: /data/prompt-config-chatmock.json
state_group: shared-auth-default
compose_service_name: chatmock
container_name: chatmock
env_overrides: {}
healthcheck:
  path: /health
ui:
  order: 10
  mutable_fields:
    - profile_id
    - port
enabled: true
```

Exact file for `config/instances/chatmock-clawmem.yaml`:

```yaml
id: chatmock-clawmem
label: ChatMock ClawMem
profile_id: clawmem
bind_host: 127.0.0.1
port: 8001
runtime: docker_compose
prompt_config_path: /data/prompt-config-chatmock-clawmem.json
state_group: shared-auth-default
compose_service_name: chatmock-clawmem
container_name: chatmock-clawmem
env_overrides: {}
healthcheck:
  path: /health
ui:
  order: 20
  mutable_fields:
    - profile_id
    - port
enabled: true
```

## Validation Rules

`chatmock/profile_registry.py` must validate:

- required keys: `id`, `label`, `description`, `prompt_dir`, `base_prompt_file`, `codex_prompt_file`, `runtime_defaults`, `ui`
- `id` matches `^[a-z0-9-]+$`
- `prompt_dir` is repo-relative and exists
- `base_prompt_file` and `codex_prompt_file` exist under `prompt_dir`
- `runtime_defaults.inject_default_instructions` is a boolean
- `ui.order` is an integer
- `ui.editable` is a boolean

`chatmock/instance_registry.py` must validate:

- required keys: `id`, `label`, `profile_id`, `bind_host`, `port`, `runtime`, `prompt_config_path`, `state_group`, `compose_service_name`, `container_name`, `env_overrides`, `healthcheck`, `ui`, `enabled`
- `id` matches `^[a-z0-9-]+$`
- `profile_id` references an existing profile
- `bind_host` is a valid IP string
- `port` is an integer in `1..65535`
- `runtime` is exactly `docker_compose` in this phase
- `prompt_config_path` starts with `/data/`
- `env_overrides` is a string-to-string map
- `healthcheck.path` is exactly `/health` for the two seed instances
- `ui.order` is an integer
- `ui.mutable_fields` is a list of strings chosen from `profile_id`, `port`
- `enabled` is a boolean

Duplicate `id`, `compose_service_name`, `container_name`, and `(bind_host, port)` tuples must be rejected with deterministic error text.

## UI-Ready Control Contract

The next step after this implementation is to evaluate whether `gui.py` can be adapted or whether a new GUI should replace it. Because of that, the management layer must expose stable control seams now.

Required service-layer methods:

- `list_profiles() -> list[dict[str, Any]]`
- `get_profile(profile_id: str) -> dict[str, Any]`
- `list_instances() -> list[dict[str, Any]]`
- `get_instance(instance_id: str) -> dict[str, Any]`
- `validate_registries() -> dict[str, Any]`
- `render_instance_preview(instance_id: str) -> dict[str, Any]`
- `render_compose_preview() -> dict[str, Any]`

Preview payloads must be designed for UI use:

- stable keys
- no raw Python objects
- explicit validation errors
- resolved prompt paths
- resolved env values
- declared shared-state group
- no dependency on terminal formatting

This allows the current GUI to either:

- call the service layer directly in-process
- call thin local admin routes
- or be replaced by a new UI that consumes the same JSON shapes

without reworking the core management logic.

## Exact DTO Contract

`list_profiles()` must return:

```python
[
    {
        "id": "bare",
        "label": "Bare",
        "description": "Default low-opinion prompt set for the main ChatMock service",
        "prompt_dir": "prompts/bare",
        "base_prompt_path": "prompts/bare/prompt.md",
        "codex_prompt_path": "prompts/bare/prompt_gpt5_codex.md",
        "runtime_defaults": {"inject_default_instructions": True},
        "ui": {"order": 10, "editable": True},
    }
]
```

`list_instances()` must return:

```python
[
    {
        "id": "chatmock",
        "label": "ChatMock",
        "profile_id": "bare",
        "bind_host": "127.0.0.1",
        "port": 8000,
        "runtime": "docker_compose",
        "prompt_config_path": "/data/prompt-config-chatmock.json",
        "state_group": "shared-auth-default",
        "compose_service_name": "chatmock",
        "container_name": "chatmock",
        "env_overrides": {},
        "healthcheck": {"path": "/health"},
        "ui": {"order": 10, "mutable_fields": ["profile_id", "port"]},
        "enabled": True,
    }
]
```

`validate_registries()` must return:

```python
{
    "ok": True,
    "profiles": ["bare", "clawmem"],
    "instances": ["chatmock", "chatmock-clawmem"],
    "errors": [],
}
```

`render_instance_preview("chatmock")` must return:

```python
{
    "instance": {
        "id": "chatmock",
        "label": "ChatMock",
        "profile_id": "bare",
        "compose_service_name": "chatmock",
        "container_name": "chatmock",
        "bind_host": "127.0.0.1",
        "port": 8000,
        "runtime": "docker_compose",
        "state_group": "shared-auth-default",
        "enabled": True,
    },
    "profile": {
        "id": "bare",
        "prompt_dir": "prompts/bare",
        "base_prompt_path": "prompts/bare/prompt.md",
        "codex_prompt_path": "prompts/bare/prompt_gpt5_codex.md",
    },
    "runtime": {
        "environment": {
            "CHATMOCK_PROMPT_DIR": "/app/prompts/bare",
            "CHATMOCK_PROMPT_CONFIG": "/data/prompt-config-chatmock.json",
            "CHATGPT_LOCAL_HOME": "/data",
        },
        "volumes": [
            "chatmock_data:/data",
            "./prompts:/app/prompts:ro",
        ],
        "healthcheck_path": "/health",
    },
    "validation": {
        "ok": True,
        "errors": [],
    },
}
```

`render_compose_preview()` must return:

```python
{
    "services": {
        "chatmock": {
            "container_name": "chatmock",
            "bind": "127.0.0.1:8000:8000",
            "profile_id": "bare",
            "prompt_config_path": "/data/prompt-config-chatmock.json",
        },
        "chatmock-clawmem": {
            "container_name": "chatmock-clawmem",
            "bind": "127.0.0.1:8001:8000",
            "profile_id": "clawmem",
            "prompt_config_path": "/data/prompt-config-chatmock-clawmem.json",
        },
    },
    "state_groups": {
        "shared-auth-default": ["chatmock", "chatmock-clawmem"],
    },
}
```

## HTTP Contract

Add:

- `GET /admin/profiles`
- `GET /admin/instances`
- `GET /admin/instances/<instance_id>/preview`

Response examples:

`GET /admin/profiles`

```json
{
  "profiles": [
    {
      "id": "bare",
      "label": "Bare",
      "description": "Default low-opinion prompt set for the main ChatMock service",
      "prompt_dir": "prompts/bare",
      "base_prompt_path": "prompts/bare/prompt.md",
      "codex_prompt_path": "prompts/bare/prompt_gpt5_codex.md",
      "runtime_defaults": {"inject_default_instructions": true},
      "ui": {"order": 10, "editable": true}
    },
    {
      "id": "clawmem",
      "label": "ClawMem",
      "description": "ClawMem-specific prompt set for the secondary managed service",
      "prompt_dir": "prompts/clawmem",
      "base_prompt_path": "prompts/clawmem/prompt.md",
      "codex_prompt_path": "prompts/clawmem/prompt_gpt5_codex.md",
      "runtime_defaults": {"inject_default_instructions": true},
      "ui": {"order": 20, "editable": true}
    }
  ]
}
```

`GET /admin/instances`

```json
{
  "instances": [
    {
      "id": "chatmock",
      "label": "ChatMock",
      "profile_id": "bare",
      "bind_host": "127.0.0.1",
      "port": 8000,
      "runtime": "docker_compose",
      "prompt_config_path": "/data/prompt-config-chatmock.json",
      "state_group": "shared-auth-default",
      "compose_service_name": "chatmock",
      "container_name": "chatmock",
      "env_overrides": {},
      "healthcheck": {"path": "/health"},
      "ui": {"order": 10, "mutable_fields": ["profile_id", "port"]},
      "enabled": true
    }
  ]
}
```

`GET /admin/instances/chatmock/preview`

```json
{
  "instance": {
    "id": "chatmock",
    "label": "ChatMock",
    "profile_id": "bare",
    "compose_service_name": "chatmock",
    "container_name": "chatmock",
    "bind_host": "127.0.0.1",
    "port": 8000,
    "runtime": "docker_compose",
    "state_group": "shared-auth-default",
    "enabled": true
  },
  "profile": {
    "id": "bare",
    "prompt_dir": "prompts/bare",
    "base_prompt_path": "prompts/bare/prompt.md",
    "codex_prompt_path": "prompts/bare/prompt_gpt5_codex.md"
  },
  "runtime": {
    "environment": {
      "CHATMOCK_PROMPT_DIR": "/app/prompts/bare",
      "CHATMOCK_PROMPT_CONFIG": "/data/prompt-config-chatmock.json",
      "CHATGPT_LOCAL_HOME": "/data"
    },
    "volumes": [
      "chatmock_data:/data",
      "./prompts:/app/prompts:ro"
    ],
    "healthcheck_path": "/health"
  },
  "validation": {
    "ok": true,
    "errors": []
  }
}
```

Errors for the new endpoints must match the existing admin style:

```json
{
  "error": {
    "message": "Unknown instance id: does-not-exist"
  }
}
```

Status code: `404`

## CLI Contract

Extend the current top-level parser with a new `instances` subparser:

```text
chatmock instances list
chatmock instances validate
chatmock instances preview <instance_id>
```

Expected output:

`chatmock instances list`

```text
chatmock            127.0.0.1:8000  profile=bare     state_group=shared-auth-default
chatmock-clawmem    127.0.0.1:8001  profile=clawmem  state_group=shared-auth-default
```

`chatmock instances validate`

```text
OK: profiles=2 instances=2 errors=0
```

Exit code: `0` on success, `1` if validation errors exist.

`chatmock instances preview chatmock`

```json
{
  "instance": {
    "id": "chatmock",
    "label": "ChatMock",
    "profile_id": "bare",
    "compose_service_name": "chatmock",
    "container_name": "chatmock",
    "bind_host": "127.0.0.1",
    "port": 8000,
    "runtime": "docker_compose",
    "state_group": "shared-auth-default",
    "enabled": true
  },
  "profile": {
    "id": "bare",
    "prompt_dir": "prompts/bare",
    "base_prompt_path": "prompts/bare/prompt.md",
    "codex_prompt_path": "prompts/bare/prompt_gpt5_codex.md"
  },
  "runtime": {
    "environment": {
      "CHATMOCK_PROMPT_DIR": "/app/prompts/bare",
      "CHATMOCK_PROMPT_CONFIG": "/data/prompt-config-chatmock.json",
      "CHATGPT_LOCAL_HOME": "/data"
    },
    "volumes": [
      "chatmock_data:/data",
      "./prompts:/app/prompts:ro"
    ],
    "healthcheck_path": "/health"
  },
  "validation": {
    "ok": true,
    "errors": []
  }
}
```

Exit code: `0` for a known instance, `1` for an unknown instance or validation failure.

## Delivery Strategy

Phase 1 should stop at **registry + validation + preview**.

That gives the upcoming GUI evaluation a stable backend contract before any heavier provisioning work is layered on top.

Phase 2 can add lifecycle/provisioning once preview parity is proven.

## Recommended Task Decomposition

### Task 1: Canonicalize the current prompt/profile and instance baseline

**Files:**
- Modify: `pyproject.toml`
- Create: `config/profiles/bare.yaml`
- Create: `config/profiles/clawmem.yaml`
- Create: `config/instances/chatmock.yaml`
- Create: `config/instances/chatmock-clawmem.yaml`
- Test: `tests/test_profile_registry.py`
- Test: `tests/test_instance_registry.py`

- [ ] **Step 1: Write failing registry tests for the current baseline**

Add exact tests:

```python
def test_load_profiles_returns_bare_and_clawmem(tmp_path: Path) -> None:
    config_root = tmp_path / "config" / "profiles"
    prompts_root = tmp_path / "prompts"
    (prompts_root / "bare").mkdir(parents=True)
    (prompts_root / "clawmem").mkdir(parents=True)
    (prompts_root / "bare" / "prompt.md").write_text("bare base", encoding="utf-8")
    (prompts_root / "bare" / "prompt_gpt5_codex.md").write_text("bare codex", encoding="utf-8")
    (prompts_root / "clawmem" / "prompt.md").write_text("clawmem base", encoding="utf-8")
    (prompts_root / "clawmem" / "prompt_gpt5_codex.md").write_text("clawmem codex", encoding="utf-8")
    config_root.mkdir(parents=True)
    (config_root / "bare.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")
    (config_root / "clawmem.yaml").write_text(CLAWMEM_PROFILE_YAML, encoding="utf-8")

    profiles = load_profiles(config_root, repo_root=tmp_path)

    assert [profile["id"] for profile in profiles] == ["bare", "clawmem"]

def test_load_instances_returns_chatmock_and_chatmock_clawmem(tmp_path: Path) -> None:
    instances_root = tmp_path / "config" / "instances"
    instances_root.mkdir(parents=True)
    (instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML, encoding="utf-8")
    (instances_root / "chatmock-clawmem.yaml").write_text(CHATMOCK_CLAWMEM_INSTANCE_YAML, encoding="utf-8")

    instances = load_instances(instances_root)

    assert [instance["id"] for instance in instances] == ["chatmock", "chatmock-clawmem"]

def test_instance_profile_reference_must_exist(tmp_path: Path) -> None:
    profiles = [{"id": "bare"}]
    instances_root = tmp_path / "config" / "instances"
    instances_root.mkdir(parents=True)
    (instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML.replace("profile_id: bare", "profile_id: missing"), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown profile_id: missing"):
        load_instances(instances_root, known_profile_ids={profile["id"] for profile in profiles})

def test_duplicate_profile_id_is_rejected(tmp_path: Path) -> None:
    config_root = tmp_path / "config" / "profiles"
    prompts_root = tmp_path / "prompts" / "bare"
    prompts_root.mkdir(parents=True)
    (prompts_root / "prompt.md").write_text("base", encoding="utf-8")
    (prompts_root / "prompt_gpt5_codex.md").write_text("codex", encoding="utf-8")
    config_root.mkdir(parents=True)
    (config_root / "a.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")
    (config_root / "b.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate profile id: bare"):
        load_profiles(config_root, repo_root=tmp_path)

def test_duplicate_instance_port_binding_is_rejected(tmp_path: Path) -> None:
    instances_root = tmp_path / "config" / "instances"
    instances_root.mkdir(parents=True)
    (instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML, encoding="utf-8")
    duplicate = CHATMOCK_CLAWMEM_INSTANCE_YAML.replace("port: 8001", "port: 8000").replace("id: chatmock-clawmem", "id: duplicate")
    (instances_root / "duplicate.yaml").write_text(duplicate, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate bind target: 127.0.0.1:8000"):
        load_instances(instances_root, known_profile_ids={"bare", "clawmem"})
```

- [ ] **Step 2: Run the new registry tests to confirm they fail**

Run:

```bash
./.venv/bin/python -m pytest tests/test_profile_registry.py tests/test_instance_registry.py -v
```

Expected: FAIL because the registries and config files do not exist yet.

- [ ] **Step 3: Add the canonical YAML config files**

Seed the registry from the current live baseline:
- `prompts/bare`
- `prompts/clawmem`
- `chatmock` on `8000`
- `chatmock-clawmem` on `8001`
- shared current state group reflecting the live shared `/data` behavior

- [ ] **Step 4: Implement registry loaders and validators**

Add:
- `chatmock/profile_registry.py`
- `chatmock/instance_registry.py`

They must:
- load YAML from `config/profiles/*.yaml` and `config/instances/*.yaml`
- use `PyYAML`
- validate required fields
- validate file/path existence for prompt files
- reject duplicate ids
- return deterministic error messages

- [ ] **Step 5: Re-run the registry tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_profile_registry.py tests/test_instance_registry.py -v
```

Expected: PASS

### Task 2: Add a reusable management service for CLI, HTTP, and GUI consumers

**Files:**
- Create: `chatmock/instance_service.py`
- Test: `tests/test_instance_service.py`

- [ ] **Step 1: Write failing service tests for listing, validation, and preview**

Cover:
- `list_profiles()`
- `list_instances()`
- `validate_registries()`
- `render_instance_preview("chatmock")`
- `render_compose_preview()`

The preview must include:
- resolved prompt dir
- resolved prompt config path
- resolved bind host and port
- state group
- env overrides

Add exact tests:

```python
def test_list_profiles_returns_stable_profile_dicts(tmp_path: Path) -> None:
    service = build_instance_service(tmp_path)

    profiles = service.list_profiles()

    assert profiles == [
        {
            "id": "bare",
            "label": "Bare",
            "description": "Default low-opinion prompt set for the main ChatMock service",
            "prompt_dir": "prompts/bare",
            "base_prompt_path": "prompts/bare/prompt.md",
            "codex_prompt_path": "prompts/bare/prompt_gpt5_codex.md",
            "runtime_defaults": {"inject_default_instructions": True},
            "ui": {"order": 10, "editable": True},
        },
        {
            "id": "clawmem",
            "label": "ClawMem",
            "description": "ClawMem-specific prompt set for the secondary managed service",
            "prompt_dir": "prompts/clawmem",
            "base_prompt_path": "prompts/clawmem/prompt.md",
            "codex_prompt_path": "prompts/clawmem/prompt_gpt5_codex.md",
            "runtime_defaults": {"inject_default_instructions": True},
            "ui": {"order": 20, "editable": True},
        },
    ]

def test_list_instances_returns_stable_instance_dicts(tmp_path: Path) -> None:
    service = build_instance_service(tmp_path)

    instances = service.list_instances()

    assert [item["id"] for item in instances] == ["chatmock", "chatmock-clawmem"]
    assert instances[0]["prompt_config_path"] == "/data/prompt-config-chatmock.json"
    assert instances[1]["prompt_config_path"] == "/data/prompt-config-chatmock-clawmem.json"

def test_validate_registries_returns_ok_summary(tmp_path: Path) -> None:
    service = build_instance_service(tmp_path)

    summary = service.validate_registries()

    assert summary == {
        "ok": True,
        "profiles": ["bare", "clawmem"],
        "instances": ["chatmock", "chatmock-clawmem"],
        "errors": [],
    }

def test_render_instance_preview_returns_expected_runtime_fields(tmp_path: Path) -> None:
    service = build_instance_service(tmp_path)

    preview = service.render_instance_preview("chatmock")

    assert preview["instance"]["id"] == "chatmock"
    assert preview["profile"]["id"] == "bare"
    assert preview["runtime"]["environment"]["CHATMOCK_PROMPT_DIR"] == "/app/prompts/bare"
    assert preview["runtime"]["environment"]["CHATMOCK_PROMPT_CONFIG"] == "/data/prompt-config-chatmock.json"
    assert preview["validation"] == {"ok": True, "errors": []}

def test_render_compose_preview_groups_instances_by_state_group(tmp_path: Path) -> None:
    service = build_instance_service(tmp_path)

    preview = service.render_compose_preview()

    assert preview["services"]["chatmock"]["bind"] == "127.0.0.1:8000:8000"
    assert preview["services"]["chatmock-clawmem"]["bind"] == "127.0.0.1:8001:8000"
    assert preview["state_groups"] == {
        "shared-auth-default": ["chatmock", "chatmock-clawmem"],
    }
```

- [ ] **Step 2: Run the service tests to confirm failure**

Run:

```bash
./.venv/bin/python -m pytest tests/test_instance_service.py -v
```

Expected: FAIL because the service layer does not exist yet.

- [ ] **Step 3: Implement the management service**

The service must:
- compose registry data into UI/API-safe dictionaries
- keep route/CLI code thin
- avoid terminal-specific formatting
- avoid Flask request coupling
- expose a preview model that can later be shown in the existing GUI without transformation-heavy glue code

- [ ] **Step 4: Re-run the service tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_instance_service.py -v
```

Expected: PASS

### Task 3: Expose read/preview controls through CLI and local admin endpoints

**Files:**
- Modify: `chatmock/app.py`
- Modify: `chatmock/cli.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing route and CLI coverage**

Add coverage for:
- `GET /admin/profiles`
- `GET /admin/instances`
- `GET /admin/instances/<id>/preview`
- CLI commands for:
  - `chatmock instances list`
  - `chatmock instances validate`
  - `chatmock instances preview <id>`

Add exact tests:

```python
def test_admin_profiles_returns_profile_list(self) -> None:
    app = create_app(admin_token=ADMIN_TOKEN)
    client = app.test_client()

    response = client.get("/admin/profiles", headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN})

    assert response.status_code == 200
    assert [item["id"] for item in response.get_json()["profiles"]] == ["bare", "clawmem"]

def test_admin_instances_returns_instance_list(self) -> None:
    app = create_app(admin_token=ADMIN_TOKEN)
    client = app.test_client()

    response = client.get("/admin/instances", headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN})

    assert response.status_code == 200
    assert [item["id"] for item in response.get_json()["instances"]] == ["chatmock", "chatmock-clawmem"]

def test_admin_instance_preview_returns_chatmock_preview(self) -> None:
    app = create_app(admin_token=ADMIN_TOKEN)
    client = app.test_client()

    response = client.get("/admin/instances/chatmock/preview", headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN})

    assert response.status_code == 200
    assert response.get_json()["instance"]["id"] == "chatmock"
    assert response.get_json()["profile"]["id"] == "bare"

def test_admin_instance_preview_returns_404_for_unknown_instance(self) -> None:
    app = create_app(admin_token=ADMIN_TOKEN)
    client = app.test_client()

    response = client.get("/admin/instances/does-not-exist/preview", headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN})

    assert response.status_code == 404
    assert response.get_json() == {
        "error": {"message": "Unknown instance id: does-not-exist"}
    }
```

CLI tests may live in a new `tests/test_cli.py` if that proves cleaner than route-only coverage.

Exact CLI tests:

```python
def test_instances_list_prints_two_seed_instances(capsys, monkeypatch) -> None:
    monkeypatch.setattr("chatmock.cli.build_instance_service", lambda: fake_service)

    exit_code = main(["instances", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "chatmock            127.0.0.1:8000  profile=bare" in captured.out
    assert "chatmock-clawmem    127.0.0.1:8001  profile=clawmem" in captured.out

def test_instances_validate_returns_nonzero_on_errors(capsys, monkeypatch) -> None:
    monkeypatch.setattr("chatmock.cli.build_instance_service", lambda: fake_service_with_errors)

    exit_code = main(["instances", "validate"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: profiles=2 instances=2 errors=1" in captured.out

def test_instances_preview_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr("chatmock.cli.build_instance_service", lambda: fake_service)

    exit_code = main(["instances", "preview", "chatmock"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["instance"]["id"] == "chatmock"
```

Parser wiring to add in `chatmock/cli.py`:

```python
p_instances = sub.add_parser("instances", help="Inspect managed ChatMock instances")
instances_sub = p_instances.add_subparsers(dest="instances_command", required=True)

p_instances_list = instances_sub.add_parser("list", help="List managed instances")
p_instances_validate = instances_sub.add_parser("validate", help="Validate managed profiles and instances")
p_instances_preview = instances_sub.add_parser("preview", help="Render preview for one managed instance")
p_instances_preview.add_argument("instance_id")
```

- [ ] **Step 2: Run the focused route and CLI tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_profiles or admin_instances" -v
```

Expected: FAIL because those controls do not exist yet.

- [ ] **Step 3: Implement thin wrappers over `instance_service`**

Rules:
- Flask routes must only marshal HTTP in/out and call the service layer
- CLI commands must only marshal terminal in/out and call the service layer
- route payloads must stay JSON-first so the GUI evaluation can reuse them later if desired

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_profiles or admin_instances" -v
```

Expected: PASS

### Task 4: Add compose-parity checks and operator docs without forcing generated runtime adoption

**Files:**
- Modify: `docker-compose.yml`
- Modify: `DOCKER.md`
- Create: `docs/chatmock-instance-management.md`

- [ ] **Step 1: Add preview parity assertions in tests**

Add or extend tests to assert the service preview matches the live Compose baseline for:
- service name
- container name
- bind host and port
- prompt dir env
- prompt config env
- volume mounts
- shared state group membership

- [ ] **Step 2: Run the compose-preview slice**

Run:

```bash
./.venv/bin/python -m pytest tests/test_instance_service.py -k "compose or preview" -v
```

Expected: PASS once preview parity is implemented.

- [ ] **Step 3: Document the operating model**

Document:
- registries are now the source of truth for managed definitions
- `docker-compose.yml` remains the live runtime entrypoint in this phase
- prompt admin routes still handle live prompt switching
- instance/profile controls currently cover inspect, validate, and preview
- lifecycle/provisioning is intentionally deferred until after the GUI decision and preview-parity validation

- [ ] **Step 4: Verify docs/config consistency**

Run:

```bash
git diff -- pyproject.toml DOCKER.md docs/chatmock-instance-management.md docker-compose.yml config/profiles config/instances
```

Expected: docs describe registry-backed inspect/preview behavior and do not claim full provisioning yet.

### Task 5: Full verification and branch hygiene

**Files:**
- Test: `tests/test_profile_registry.py`
- Test: `tests/test_instance_registry.py`
- Test: `tests/test_instance_service.py`
- Test: `tests/test_routes.py`

- [ ] **Step 1: Run the new management test modules**

```bash
./.venv/bin/python -m pytest tests/test_profile_registry.py tests/test_instance_registry.py tests/test_instance_service.py -v
```

- [ ] **Step 2: Run the focused route regression slice**

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_prompts or admin_profiles or admin_instances" -v
```

- [ ] **Step 3: Check for unintended drift**

```bash
git status --short
git diff -- pyproject.toml chatmock/app.py chatmock/cli.py chatmock/profile_registry.py chatmock/instance_registry.py chatmock/instance_service.py tests/test_profile_registry.py tests/test_instance_registry.py tests/test_instance_service.py tests/test_routes.py tests/test_cli.py docker-compose.yml DOCKER.md docs/chatmock-instance-management.md config/profiles config/instances
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml chatmock/app.py chatmock/cli.py chatmock/profile_registry.py chatmock/instance_registry.py chatmock/instance_service.py tests/test_profile_registry.py tests/test_instance_registry.py tests/test_instance_service.py tests/test_routes.py tests/test_cli.py docker-compose.yml DOCKER.md docs/chatmock-instance-management.md config/profiles config/instances docs/superpowers/plans/2026-04-22-chatmock-profile-instance-management.md
git commit -m "feat: add registry-backed instance management previews"
```

## Risks And Guardrails

- **State collision remains real on `dev`:**
  both live services still share the same `/data` volume.
  Guardrail: model this explicitly as `state_group` and surface it in previews instead of hiding it.

- **Generated-runtime churn is high risk right now:**
  forcing `docker-compose.generated.yml` too early would create noise and parity risk.
  Guardrail: phase 1 stops at preview and parity checks.

- **GUI coupling risk:**
  if route handlers own all of the logic, the current PySide GUI cannot reuse it cleanly.
  Guardrail: keep management logic in `instance_service.py` and make CLI/HTTP wrappers thin.

- **Prompt control duplication risk:**
  building a second prompt-switching mechanism inside the registry layer would fight `PromptManager`.
  Guardrail: profile/instance management defines defaults and previews; `PromptManager` remains the live runtime owner.

## Implementation Handoff Notes

- The implementation branch must start from `dev`, not from the live-prompt-reload review branch, because `dev` already contains the prompt manager/admin baseline this plan depends on.
- Do not build or modify GUI controls in this phase.
- Do shape the service and route payloads so the next phase can evaluate `gui.py` with minimal backend change.
- If the upcoming GUI evaluation decides to replace `gui.py`, the replacement should still be able to consume the same `instance_service` outputs or local admin JSON payloads.
