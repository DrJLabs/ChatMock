from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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


class InstanceServiceTests(unittest.TestCase):
    def _write_prompt_set(self, root: Path, profile: str) -> None:
        prompt_dir = root / "prompts" / profile
        prompt_dir.mkdir(parents=True, exist_ok=True)
        (prompt_dir / "prompt.md").write_text(f"{profile} base", encoding="utf-8")
        (prompt_dir / "prompt_gpt5_codex.md").write_text(f"{profile} codex", encoding="utf-8")

    def _write_registry(self, root: Path) -> None:
        self._write_prompt_set(root, "bare")
        self._write_prompt_set(root, "clawmem")
        profiles_root = root / "config" / "profiles"
        instances_root = root / "config" / "instances"
        profiles_root.mkdir(parents=True, exist_ok=True)
        instances_root.mkdir(parents=True, exist_ok=True)
        (profiles_root / "bare.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")
        (profiles_root / "clawmem.yaml").write_text(CLAWMEM_PROFILE_YAML, encoding="utf-8")
        (instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML, encoding="utf-8")
        (instances_root / "chatmock-clawmem.yaml").write_text(CHATMOCK_CLAWMEM_INSTANCE_YAML, encoding="utf-8")

    def test_list_profiles_returns_stable_profile_dicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_registry(root)
            service = build_instance_service(repo_root=root)

            profiles = service.list_profiles()

            self.assertEqual(
                profiles,
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
                ],
            )

    def test_list_instances_returns_stable_instance_dicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_registry(root)
            service = build_instance_service(repo_root=root)

            instances = service.list_instances()

            self.assertEqual([item["id"] for item in instances], ["chatmock", "chatmock-clawmem"])
            self.assertEqual(instances[0]["prompt_config_path"], "/data/prompt-config-chatmock.json")
            self.assertEqual(instances[1]["prompt_config_path"], "/data/prompt-config-chatmock-clawmem.json")

    def test_validate_registries_returns_ok_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_registry(root)
            service = build_instance_service(repo_root=root)

            summary = service.validate_registries()

            self.assertEqual(
                summary,
                {
                    "ok": True,
                    "profiles": ["bare", "clawmem"],
                    "instances": ["chatmock", "chatmock-clawmem"],
                    "errors": [],
                },
            )

    def test_render_instance_preview_returns_expected_runtime_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_registry(root)
            service = build_instance_service(repo_root=root)

            preview = service.render_instance_preview("chatmock")

            self.assertEqual(preview["instance"]["id"], "chatmock")
            self.assertEqual(preview["profile"]["id"], "bare")
            self.assertEqual(preview["runtime"]["environment"]["CHATMOCK_PROMPT_DIR"], "/app/prompts/bare")
            self.assertEqual(preview["runtime"]["environment"]["CHATMOCK_PROMPT_CONFIG"], "/data/prompt-config-chatmock.json")
            self.assertEqual(preview["validation"], {"ok": True, "errors": []})

    def test_render_compose_preview_groups_instances_by_state_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_registry(root)
            service = build_instance_service(repo_root=root)

            preview = service.render_compose_preview()

            self.assertEqual(preview["services"]["chatmock"]["bind"], "127.0.0.1:8000:8000")
            self.assertEqual(preview["services"]["chatmock-clawmem"]["bind"], "127.0.0.1:8001:8000")
            self.assertEqual(
                preview["state_groups"],
                {"shared-auth-default": ["chatmock", "chatmock-clawmem"]},
            )
