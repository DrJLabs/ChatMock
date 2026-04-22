# Live Prompt Reload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only admin HTTP API that can switch and reload prompt paths live, using a file-backed runtime prompt config and cached prompt contents without restarting the ChatMock process.

**Architecture:** Introduce a prompt manager in `chatmock/config.py` that owns service-specific runtime prompt config, cached prompt text, and reload/update operations. Wire request-time instruction resolution through that manager, add loopback-only admin routes in `chatmock/app.py`, and update Docker wiring so each service mounts a stable prompt root plus its own runtime config path under `/data`.

**Tech Stack:** Flask, unittest, tempfile, Docker Compose

---

## File Structure

- Modify `chatmock/config.py`
  - Add the prompt manager, runtime config persistence, validation, and cache reload logic.
- Modify `chatmock/app.py`
  - Register the prompt manager on the app and add the local-only admin routes.
- Modify `chatmock/responses_api.py`
  - Resolve instructions from the prompt manager cache instead of startup-loaded globals.
- Modify `tests/test_routes.py`
  - Add route-level coverage for inspect, reload, config update, and local-only guard behavior.
- Modify `docker-compose.yml`
  - Replace direct prompt-file mounts with a stable prompts-root mount and distinct runtime config env vars per service.
- Modify `.env.example`
  - Document the new prompt runtime env vars.
- Modify `DOCKER.md`
  - Document how live prompt config and reload work.

### Task 1: Prompt manager and runtime config

**Files:**
- Modify: `chatmock/config.py`

- [ ] **Step 1: Write the failing tests for runtime prompt management**

Add route tests that exercise:
- live reload after editing prompt files
- config update to a different prompt directory
- rejection of invalid prompt paths

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_prompts" -v
```

Expected: FAIL because no prompt admin routes or runtime prompt manager exist yet.

- [ ] **Step 3: Implement the prompt manager**

Add a manager that:
- loads defaults from env or legacy prompt resolution
- persists service-specific runtime config to `${CHATGPT_LOCAL_PROMPT_CONFIG}`
- caches prompt text in memory
- exposes `get_state()`, `reload()`, and `update_config(...)`

- [ ] **Step 4: Run the targeted tests again**

Run:

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_prompts" -v
```

Expected: still FAIL until the admin routes are wired.

### Task 2: Admin endpoints and request-path integration

**Files:**
- Modify: `chatmock/app.py`
- Modify: `chatmock/responses_api.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Add failing route tests for the admin API**

Cover:
- `GET /admin/prompts` returns current config and cache metadata
- `POST /admin/prompts/reload` refreshes cached prompt text
- `POST /admin/prompts/config` switches prompt directories live
- non-loopback access is rejected

- [ ] **Step 2: Run those route tests to confirm failure**

Run:

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_prompts or prompt_reload" -v
```

Expected: FAIL with `404` or missing behavior.

- [ ] **Step 3: Implement the admin routes and integration**

Wire:
- one shared prompt manager into `create_app()`
- loopback-only guard in `app.py`
- `resolve_effective_instructions(...)` to use cached prompt text from the prompt manager

- [ ] **Step 4: Run the focused route tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_prompts or prompt_reload" -v
```

Expected: PASS

### Task 3: Docker/runtime wiring

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `DOCKER.md`

- [ ] **Step 1: Update compose to mount the whole prompts tree**

Replace direct prompt file mounts with a stable root mount:

```yaml
- ./prompts:/app/prompts:ro
```

and set per-service env defaults such as:

```yaml
- CHATGPT_LOCAL_PROMPT_DIR=/app/prompts/bare
- CHATGPT_LOCAL_PROMPT_CONFIG=/data/prompt-config-chatmock.json
```

and for the ClawMem service:

```yaml
- CHATGPT_LOCAL_PROMPT_DIR=/app/prompts/clawmem
- CHATGPT_LOCAL_PROMPT_CONFIG=/data/prompt-config-clawmem.json
```

- [ ] **Step 2: Document the new env vars**

Add to `.env.example` and `DOCKER.md`:
- `CHATGPT_LOCAL_PROMPT_DIR`
- `CHATGPT_LOCAL_PROMPT_BASE_PATH`
- `CHATGPT_LOCAL_PROMPT_CODEX_PATH`
- `CHATGPT_LOCAL_PROMPT_CONFIG`
- optional admin token env if implemented

- [ ] **Step 3: Verify the docs/config slice**

Run:

```bash
git diff -- docker-compose.yml .env.example DOCKER.md
```

Expected: prompt path control is documented and each service has a distinct runtime config file.

### Task 4: Full verification

**Files:**
- Test: `tests/test_routes.py`

- [ ] **Step 1: Run the focused prompt-admin slice**

```bash
./.venv/bin/python -m pytest tests/test_routes.py -k "admin_prompts or prompt_reload" -v
```

- [ ] **Step 2: Run the full route regression module**

```bash
./.venv/bin/python -m pytest tests/test_routes.py -v
```

- [ ] **Step 3: Verify no unintended branch drift**

```bash
git status --short
git diff -- chatmock/config.py chatmock/app.py chatmock/responses_api.py tests/test_routes.py docker-compose.yml .env.example DOCKER.md
```

- [ ] **Step 4: Commit**

```bash
git add chatmock/config.py chatmock/app.py chatmock/responses_api.py tests/test_routes.py docker-compose.yml .env.example DOCKER.md docs/superpowers/specs/2026-04-22-live-prompt-reload-design.md docs/superpowers/plans/2026-04-22-live-prompt-reload.md
git commit -m "feat: add live prompt reload controls"
```
