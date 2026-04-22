from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from chatmock.cli import main


class _FakeService:
    def list_instances(self):
        return [
            {
                "id": "chatmock",
                "bind_host": "127.0.0.1",
                "port": 8000,
                "profile_id": "bare",
                "state_group": "shared-auth-default",
            },
            {
                "id": "chatmock-clawmem",
                "bind_host": "127.0.0.1",
                "port": 8001,
                "profile_id": "clawmem",
                "state_group": "shared-auth-default",
            },
        ]

    def validate_registries(self):
        return {
            "ok": True,
            "profiles": ["bare", "clawmem"],
            "instances": ["chatmock", "chatmock-clawmem"],
            "errors": [],
        }

    def render_instance_preview(self, instance_id: str):
        if instance_id != "chatmock":
            raise ValueError(f"Unknown instance id: {instance_id}")
        return {
            "instance": {"id": "chatmock"},
            "profile": {"id": "bare"},
            "runtime": {},
            "validation": {"ok": True, "errors": []},
        }


class _FakeServiceWithErrors(_FakeService):
    def validate_registries(self):
        return {
            "ok": False,
            "profiles": ["bare", "clawmem"],
            "instances": ["chatmock", "chatmock-clawmem"],
            "errors": ["duplicate bind target"],
        }


class CliTests(unittest.TestCase):
    @patch("chatmock.cli.build_instance_service", return_value=_FakeService())
    def test_instances_list_prints_two_seed_instances(self, _mock_service) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["instances", "list"])

        self.assertEqual(exit_code, 0)
        self.assertIn("chatmock            127.0.0.1:8000  profile=bare", buffer.getvalue())
        self.assertIn("chatmock-clawmem    127.0.0.1:8001  profile=clawmem", buffer.getvalue())

    @patch("chatmock.cli.build_instance_service", return_value=_FakeServiceWithErrors())
    def test_instances_validate_returns_nonzero_on_errors(self, _mock_service) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["instances", "validate"])

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: profiles=2 instances=2 errors=1", buffer.getvalue())

    @patch("chatmock.cli.build_instance_service", return_value=_FakeService())
    def test_instances_preview_prints_json(self, _mock_service) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["instances", "preview", "chatmock"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(buffer.getvalue())["instance"]["id"], "chatmock")

    @patch("chatmock.cli.build_instance_service", side_effect=ValueError("registry broken"))
    def test_instances_commands_return_nonzero_when_registry_build_fails(self, _mock_service) -> None:
        for argv in (["instances", "list"], ["instances", "validate"], ["instances", "preview", "chatmock"]):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(argv)
            self.assertEqual(exit_code, 1)
            self.assertIn("registry broken", buffer.getvalue())
