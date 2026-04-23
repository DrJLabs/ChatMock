from __future__ import annotations
from pathlib import Path

from chatmock.app import create_app


def _write_admin_index(dist_dir: Path, body: str = "<h1>ChatMock Admin</h1>") -> None:
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text(body, encoding="utf-8")


BARE_PROFILE_YAML = """\
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
"""


CLAWMEM_PROFILE_YAML = """\
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
"""


CHATMOCK_INSTANCE_YAML = """\
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
env_prefix: CHATMOCK
env_overrides: {}
healthcheck:
  path: /health
ui:
  order: 10
  mutable_fields:
    - profile_id
    - port
enabled: true
"""


CHATMOCK_CLAWMEM_INSTANCE_YAML = """\
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
env_prefix: CHATMOCK_CLAWMEM
env_overrides: {}
healthcheck:
  path: /health
ui:
  order: 20
  mutable_fields:
    - profile_id
    - port
enabled: true
"""


def _write_prompt_set(root: Path, profile: str) -> None:
    prompt_dir = root / "prompts" / profile
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "prompt.md").write_text(f"{profile} base", encoding="utf-8")
    (prompt_dir / "prompt_gpt5_codex.md").write_text(f"{profile} codex", encoding="utf-8")


def _write_registry(root: Path) -> None:
    _write_prompt_set(root, "bare")
    _write_prompt_set(root, "clawmem")
    profiles_root = root / "config" / "profiles"
    instances_root = root / "config" / "instances"
    profiles_root.mkdir(parents=True, exist_ok=True)
    instances_root.mkdir(parents=True, exist_ok=True)
    (profiles_root / "bare.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")
    (profiles_root / "clawmem.yaml").write_text(CLAWMEM_PROFILE_YAML, encoding="utf-8")
    (instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML, encoding="utf-8")
    (instances_root / "chatmock-clawmem.yaml").write_text(CHATMOCK_CLAWMEM_INSTANCE_YAML, encoding="utf-8")


def _build_admin_app(root: Path, *, runtime_redeploy_callback=None):
    _write_registry(root)
    dist_dir = root / "dist"
    _write_admin_index(dist_dir)
    prompt_dir = root / "prompts" / "bare"
    return create_app(
        admin_ui_dist_dir=str(dist_dir),
        prompt_dir=str(prompt_dir),
        prompt_config_path=str(root / "prompt-config-chatmock.json"),
        repo_root=str(root),
        runtime_redeploy_callback=runtime_redeploy_callback,
    )


def test_admin_ui_index_serves_built_assets(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    _write_admin_index(dist_dir)
    app = create_app(admin_ui_dist_dir=str(dist_dir))
    client = app.test_client()

    response = client.get("/admin/ui")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"ChatMock Admin" in response.data


def test_admin_ui_unknown_path_falls_back_to_index(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    _write_admin_index(dist_dir, "<h1>Instances</h1>")
    app = create_app(admin_ui_dist_dir=str(dist_dir))
    client = app.test_client()

    response = client.get("/admin/ui/instances")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"Instances" in response.data


def test_admin_ui_trailing_slash_serves_index(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    _write_admin_index(dist_dir, "<h1>Trailing Slash</h1>")
    app = create_app(admin_ui_dist_dir=str(dist_dir))
    client = app.test_client()

    response = client.get("/admin/ui/")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"Trailing Slash" in response.data


def test_get_draft_returns_current_state(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.get("/admin/draft")

    assert response.status_code == 200
    body = response.get_json()
    assert [profile["id"] for profile in body["profiles"]] == ["bare", "clawmem"]
    assert [instance["id"] for instance in body["instances"]] == ["chatmock", "chatmock-clawmem"]
    assert body["dirty"] is False


def test_put_profile_updates_draft_only(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.put("/admin/profiles/bare", json={"label": "Bare Updated"})

    assert response.status_code == 200
    body = response.get_json()
    assert next(profile for profile in body["profiles"] if profile["id"] == "bare")["label"] == "Bare Updated"
    current = client.get("/admin/profiles").get_json()
    assert next(profile for profile in current["profiles"] if profile["id"] == "bare")["label"] == "Bare"


def test_put_instance_updates_draft_only(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.put("/admin/instances/chatmock", json={"port": 8010})

    assert response.status_code == 200
    body = response.get_json()
    assert next(instance for instance in body["instances"] if instance["id"] == "chatmock")["port"] == 8010
    current = client.get("/admin/instances").get_json()
    assert next(instance for instance in current["instances"] if instance["id"] == "chatmock")["port"] == 8000


def test_post_draft_validate_returns_validation_summary(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.post("/admin/draft/validate")

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "errors": [],
        "profiles": ["bare", "clawmem"],
        "instances": ["chatmock", "chatmock-clawmem"],
    }


def test_post_draft_preview_returns_preview_payload(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.post("/admin/draft/preview")

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["compose_preview"]["services"]["chatmock"]["bind"] == "127.0.0.1:8000:8000"
    assert len(body["instance_previews"]) == 2


def test_post_draft_apply_persists_yaml(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()
    client.put("/admin/profiles/bare", json={"label": "Bare Updated"})
    client.put("/admin/instances/chatmock", json={"port": 8010})

    response = client.post("/admin/draft/apply")

    assert response.status_code == 200
    current_profiles = client.get("/admin/profiles").get_json()
    current_instances = client.get("/admin/instances").get_json()
    assert next(profile for profile in current_profiles["profiles"] if profile["id"] == "bare")["label"] == "Bare Updated"
    assert next(instance for instance in current_instances["instances"] if instance["id"] == "chatmock")["port"] == 8010


def test_post_runtime_validate_returns_current_registry_summary(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.post("/admin/runtime/validate")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_post_runtime_redeploy_invokes_callback(tmp_path: Path):
    called: list[dict[str, object]] = []

    def _callback():
        called.append({"ok": True})
        return {"ok": True, "status": "redeployed"}

    app = _build_admin_app(tmp_path, runtime_redeploy_callback=_callback)
    client = app.test_client()

    response = client.post("/admin/runtime/redeploy")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "status": "redeployed"}
    assert called == [{"ok": True}]


def test_prompt_file_read_returns_selected_profile_contents(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/admin/prompts/files/read",
        json={
            "base_prompt_path": "prompts/clawmem/prompt.md",
            "codex_prompt_path": "prompts/clawmem/prompt_gpt5_codex.md",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "base_prompt_path": "prompts/clawmem/prompt.md",
        "codex_prompt_path": "prompts/clawmem/prompt_gpt5_codex.md",
        "base_prompt_text": "clawmem base",
        "codex_prompt_text": "clawmem codex",
        "reloaded_current_prompt_set": False,
    }


def test_prompt_file_write_updates_disk_and_reloads_current_prompt_set(tmp_path: Path):
    app = _build_admin_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/admin/prompts/files/write",
        json={
            "base_prompt_path": "prompts/bare/prompt.md",
            "codex_prompt_path": "prompts/bare/prompt_gpt5_codex.md",
            "base_prompt_text": "bare base updated",
            "codex_prompt_text": "bare codex updated",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["base_prompt_text"] == "bare base updated"
    assert body["codex_prompt_text"] == "bare codex updated"
    assert body["reloaded_current_prompt_set"] is True
    assert (tmp_path / "prompts" / "bare" / "prompt.md").read_text(encoding="utf-8") == "bare base updated"
    assert (tmp_path / "prompts" / "bare" / "prompt_gpt5_codex.md").read_text(encoding="utf-8") == "bare codex updated"

    current_prompt_state = client.get("/admin/prompts").get_json()
    assert current_prompt_state["base_prompt_text"] == "bare base updated"
    assert current_prompt_state["codex_prompt_text"] == "bare codex updated"
