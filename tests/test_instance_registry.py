from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chatmock.instance_registry import load_instances


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


class InstanceRegistryTests(unittest.TestCase):
    def test_load_instances_returns_chatmock_and_chatmock_clawmem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instances_root = root / "config" / "instances"
            instances_root.mkdir(parents=True, exist_ok=True)
            (instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML, encoding="utf-8")
            (instances_root / "chatmock-clawmem.yaml").write_text(CHATMOCK_CLAWMEM_INSTANCE_YAML, encoding="utf-8")

            instances = load_instances(instances_root, known_profile_ids={"bare", "clawmem"})

            self.assertEqual([instance["id"] for instance in instances], ["chatmock", "chatmock-clawmem"])

    def test_instance_profile_reference_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instances_root = root / "config" / "instances"
            instances_root.mkdir(parents=True, exist_ok=True)
            bad_yaml = CHATMOCK_INSTANCE_YAML.replace("profile_id: bare", "profile_id: missing")
            (instances_root / "chatmock.yaml").write_text(bad_yaml, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unknown profile_id: missing"):
                load_instances(instances_root, known_profile_ids={"bare"})

    def test_duplicate_instance_port_binding_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instances_root = root / "config" / "instances"
            instances_root.mkdir(parents=True, exist_ok=True)
            (instances_root / "chatmock.yaml").write_text(CHATMOCK_INSTANCE_YAML, encoding="utf-8")
            duplicate = (
                CHATMOCK_CLAWMEM_INSTANCE_YAML
                .replace("id: chatmock-clawmem", "id: duplicate")
                .replace("port: 8001", "port: 8000")
            )
            (instances_root / "duplicate.yaml").write_text(duplicate, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate bind target: 127.0.0.1:8000"):
                load_instances(instances_root, known_profile_ids={"bare", "clawmem"})
