from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from chatmock.admin_draft_service import AdminDraftService
from chatmock.instance_service import build_instance_service


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


def test_reset_loads_current_profiles_and_instances():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_registry(root)
        service = AdminDraftService(repo_root=root)

        draft = service.reset()

        assert [profile["id"] for profile in draft["profiles"]] == ["bare", "clawmem"]
        assert [instance["id"] for instance in draft["instances"]] == ["chatmock", "chatmock-clawmem"]
        assert draft["dirty"] is False


def test_update_profile_only_mutates_draft():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_registry(root)
        service = AdminDraftService(repo_root=root)

        draft = service.update_profile("bare", {"label": "Bare Updated"})
        persisted = build_instance_service(repo_root=root)

        assert next(profile for profile in draft["profiles"] if profile["id"] == "bare")["label"] == "Bare Updated"
        assert persisted.get_profile("bare")["label"] == "Bare"
        assert draft["dirty"] is True


def test_update_instance_only_mutates_draft():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_registry(root)
        service = AdminDraftService(repo_root=root)

        draft = service.update_instance("chatmock", {"port": 8010})
        persisted = build_instance_service(repo_root=root)

        assert next(instance for instance in draft["instances"] if instance["id"] == "chatmock")["port"] == 8010
        assert persisted.get_instance("chatmock")["port"] == 8000
        assert draft["dirty"] is True


def test_apply_writes_yaml_and_refreshes_draft():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_registry(root)
        service = AdminDraftService(repo_root=root)
        service.update_profile("bare", {"label": "Bare Updated"})
        service.update_instance("chatmock", {"port": 8010})

        draft = service.apply()
        persisted = build_instance_service(repo_root=root)

        assert draft["dirty"] is False
        assert persisted.get_profile("bare")["label"] == "Bare Updated"
        assert persisted.get_instance("chatmock")["port"] == 8010


def test_reset_uses_explicit_registry_roots():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_registry(root)

        custom_profiles_root = root / "custom" / "profiles"
        custom_instances_root = root / "custom" / "instances"
        custom_profiles_root.mkdir(parents=True, exist_ok=True)
        custom_instances_root.mkdir(parents=True, exist_ok=True)
        (custom_profiles_root / "bare.yaml").write_text(BARE_PROFILE_YAML.replace("label: Bare", "label: Custom Bare"), encoding="utf-8")
        (custom_profiles_root / "clawmem.yaml").write_text(CLAWMEM_PROFILE_YAML, encoding="utf-8")
        (custom_instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML.replace("port: 8000", "port: 8100"), encoding="utf-8")
        (custom_instances_root / "chatmock-clawmem.yaml").write_text(CHATMOCK_CLAWMEM_INSTANCE_YAML, encoding="utf-8")

        service = AdminDraftService(
            repo_root=root,
            profiles_root=custom_profiles_root,
            instances_root=custom_instances_root,
        )

        draft = service.reset()

        assert next(profile for profile in draft["profiles"] if profile["id"] == "bare")["label"] == "Custom Bare"
        assert next(instance for instance in draft["instances"] if instance["id"] == "chatmock")["port"] == 8100


def test_apply_rolls_back_profile_directory_if_instance_swap_fails():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_registry(root)
        service = AdminDraftService(repo_root=root)
        service.update_profile("bare", {"label": "Bare Updated"})
        service.update_instance("chatmock", {"port": 8010})

        original_profile_yaml = (root / "config" / "profiles" / "bare.yaml").read_text(encoding="utf-8")

        original_swap = service._swap_staged_yaml_directory
        call_count = {"value": 0}

        def flaky_swap(target_root, staged_root):
            call_count["value"] += 1
            if call_count["value"] == 2:
                raise OSError("simulated instance swap failure")
            return original_swap(target_root, staged_root)

        with patch.object(service, "_swap_staged_yaml_directory", side_effect=flaky_swap):
            try:
                service.apply()
            except OSError as exc:
                assert "simulated instance swap failure" in str(exc)
            else:
                raise AssertionError("Expected apply() to fail during instance swap")

        assert (root / "config" / "profiles" / "bare.yaml").read_text(encoding="utf-8") == original_profile_yaml
        persisted = build_instance_service(repo_root=root)
        assert persisted.get_profile("bare")["label"] == "Bare"
        assert persisted.get_instance("chatmock")["port"] == 8000
