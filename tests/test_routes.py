from __future__ import annotations

import json
import socket
import threading
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chatmock.app import create_app
from chatmock.responses_api import (
    fallback_passthrough_instructions,
    iter_normalized_response_events,
    stream_upstream_bytes,
)
from chatmock.session import reset_session_state
from websockets.sync.client import connect as ws_connect

ADMIN_TOKEN = "test-token"


class FakeUpstream:
    def __init__(
        self,
        events: list[dict[str, object]] | None = None,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        text: str = "",
    ) -> None:
        self._events = events
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content or b""
        self.text = text

    def iter_lines(self, decode_unicode: bool = False):
        if self.content:
            for line in self.content.splitlines():
                yield line.decode("utf-8") if decode_unicode else line
            return
        for event in self._events or []:
            payload = f"data: {json.dumps(event)}"
            yield payload if decode_unicode else payload.encode("utf-8")
            yield "" if decode_unicode else b""

    def iter_content(self, chunk_size=None):
        if self.content:
            yield self.content
            return
        for event in self._events or []:
            payload = f"data: {json.dumps(event)}\n\n".encode("utf-8")
            yield payload

    def json(self):
        return json.loads(self.content.decode("utf-8"))

    def close(self) -> None:
        return None


def decode_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        for line in block.splitlines():
            if not line.startswith("data: "):
                continue
            payload = line[len("data: ") :]
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                events.append(parsed)
    return events


class RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_session_state()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_openai_models_list(self) -> None:
        response = self.client.get("/v1/models")
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        model_ids = [item["id"] for item in body["data"]]
        self.assertIn("gpt-5.4", model_ids)
        self.assertIn("gpt-5.4-mini", model_ids)
        self.assertIn("gpt-5.3-codex-spark", model_ids)

    def test_ollama_tags_list(self) -> None:
        response = self.client.get("/api/tags")
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        model_names = [item["name"] for item in body["models"]]
        self.assertIn("gpt-5.4", model_names)
        self.assertIn("gpt-5.4-mini", model_names)

    def _write_prompt_set(self, root: Path, profile: str, base_text: str, codex_text: str) -> Path:
        prompt_dir = root / profile
        prompt_dir.mkdir(parents=True, exist_ok=True)
        (prompt_dir / "prompt.md").write_text(base_text, encoding="utf-8")
        (prompt_dir / "prompt_gpt5_codex.md").write_text(codex_text, encoding="utf-8")
        return prompt_dir

    def test_admin_prompts_returns_current_prompt_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = self._write_prompt_set(root, "bare", "bare base", "bare codex")
            app = create_app(
                prompt_dir=str(prompt_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
                admin_token=ADMIN_TOKEN,
            )
            client = app.test_client()
            headers = {"X-ChatMock-Admin-Token": ADMIN_TOKEN}

            response = client.get("/admin/prompts", headers=headers)

            self.assertEqual(response.status_code, 200)
            body = response.get_json()
            self.assertEqual(body["prompt_dir"], str(prompt_dir))
            self.assertEqual(body["base_prompt_path"], str(prompt_dir / "prompt.md"))
            self.assertEqual(body["codex_prompt_path"], str(prompt_dir / "prompt_gpt5_codex.md"))

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_admin_prompts_reload_refreshes_cached_prompt_contents(self, mock_start) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = self._write_prompt_set(root, "bare", "bare base v1", "bare codex v1")
            app = create_app(
                prompt_dir=str(prompt_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
                admin_token=ADMIN_TOKEN,
            )
            client = app.test_client()
            headers = {"X-ChatMock-Admin-Token": ADMIN_TOKEN}
            mock_start.return_value = (
                FakeUpstream(
                    [
                        {"type": "response.output_text.delta", "delta": "hello"},
                        {"type": "response.completed", "response": {"id": "resp-openai"}},
                    ]
                ),
                None,
            )

            first = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-5.4", "messages": [{"role": "user", "content": "hi"}]},
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(mock_start.call_args.kwargs["instructions"], "bare base v1")

            (prompt_dir / "prompt.md").write_text("bare base v2", encoding="utf-8")
            reload_response = client.post("/admin/prompts/reload", headers=headers)
            self.assertEqual(reload_response.status_code, 200)

            second = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-5.4", "messages": [{"role": "user", "content": "hi"}]},
            )
            self.assertEqual(second.status_code, 200)
            self.assertEqual(mock_start.call_args.kwargs["instructions"], "bare base v2")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_admin_prompts_config_switches_prompt_directory_live(self, mock_start) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare_dir = self._write_prompt_set(root, "bare", "bare base", "bare codex")
            clawmem_dir = self._write_prompt_set(root, "clawmem", "clawmem base", "clawmem codex")
            app = create_app(
                prompt_dir=str(bare_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
                admin_token=ADMIN_TOKEN,
            )
            client = app.test_client()
            headers = {"X-ChatMock-Admin-Token": ADMIN_TOKEN}
            mock_start.return_value = (
                FakeUpstream(
                    [
                        {"type": "response.output_text.delta", "delta": "hello"},
                        {"type": "response.completed", "response": {"id": "resp-openai"}},
                    ]
                ),
                None,
            )

            update = client.post("/admin/prompts/config", json={"prompt_dir": str(clawmem_dir)}, headers=headers)
            self.assertEqual(update.status_code, 200)

            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-5.3-codex", "messages": [{"role": "user", "content": "hi"}]},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_start.call_args.kwargs["instructions"], "clawmem codex")

    def test_admin_prompts_rejects_non_loopback_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = self._write_prompt_set(root, "bare", "bare base", "bare codex")
            app = create_app(
                prompt_dir=str(prompt_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
            )
            client = app.test_client()

            response = client.get("/admin/prompts", environ_overrides={"REMOTE_ADDR": "10.0.0.2"})

            self.assertEqual(response.status_code, 403)

    def test_admin_prompts_rejects_missing_remote_addr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = self._write_prompt_set(root, "bare", "bare base", "bare codex")
            app = create_app(
                prompt_dir=str(prompt_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
            )
            client = app.test_client()

            response = client.get("/admin/prompts", environ_overrides={"REMOTE_ADDR": None})

            self.assertEqual(response.status_code, 403)

    @patch.dict(
        "os.environ",
        {
            "CHATMOCK_ADMIN_TRUSTED_IPS": "10.0.0.0/8",
            "CHATMOCK_ADMIN_TOKEN": "",
            "CHATGPT_LOCAL_ADMIN_TOKEN": "",
        },
    )
    def test_admin_prompts_allows_configured_trusted_ip_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = self._write_prompt_set(root, "bare", "bare base", "bare codex")
            app = create_app(
                prompt_dir=str(prompt_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
            )
            client = app.test_client()

            response = client.get("/admin/prompts", environ_overrides={"REMOTE_ADDR": "10.12.0.5"})

            self.assertEqual(response.status_code, 200)

    @patch.dict("os.environ", {"CHATMOCK_ALLOW_ADMIN_EXTERNAL": "true"})
    def test_admin_prompts_external_access_requires_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = self._write_prompt_set(root, "bare", "bare base", "bare codex")
            app = create_app(
                prompt_dir=str(prompt_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
            )
            client = app.test_client()

            response = client.get("/admin/prompts", environ_overrides={"REMOTE_ADDR": "203.0.113.9"})

            self.assertEqual(response.status_code, 403)

    def test_admin_profiles_returns_profile_list(self) -> None:
        app = create_app(admin_token=ADMIN_TOKEN)
        client = app.test_client()

        response = client.get("/admin/profiles", headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.get_json()["profiles"]], ["bare", "clawmem"])

    def test_admin_instances_returns_instance_list(self) -> None:
        app = create_app(admin_token=ADMIN_TOKEN)
        client = app.test_client()

        response = client.get("/admin/instances", headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.get_json()["instances"]], ["chatmock", "chatmock-clawmem"])

    def test_admin_instance_preview_returns_chatmock_preview(self) -> None:
        app = create_app(admin_token=ADMIN_TOKEN)
        client = app.test_client()

        response = client.get("/admin/instances/chatmock/preview", headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["instance"]["id"], "chatmock")
        self.assertEqual(response.get_json()["profile"]["id"], "bare")

    def test_admin_instance_preview_returns_404_for_unknown_instance(self) -> None:
        app = create_app(admin_token=ADMIN_TOKEN)
        client = app.test_client()

        response = client.get(
            "/admin/instances/does-not-exist/preview",
            headers={"X-ChatMock-Admin-Token": ADMIN_TOKEN},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.get_json(),
            {"error": {"message": "Unknown instance id: does-not-exist"}},
        )

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_invalid_reasoning_effort_does_not_override_nested_reasoning(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.4",
                "reasoning_effort": "bogus",
                "reasoning": {"effort": "high", "summary": "detailed"},
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["reasoning_param"]["effort"], "high")
        self.assertEqual(mock_start.call_args.kwargs["reasoning_param"]["summary"], "detailed")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_codex_prompt_falls_back_to_base_when_variant_missing(self, mock_start) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "bare"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            (prompt_dir / "prompt.md").write_text("base only", encoding="utf-8")
            app = create_app(
                prompt_dir=str(prompt_dir),
                prompt_config_path=str(root / "prompt-config-chatmock.json"),
            )
            client = app.test_client()
            mock_start.return_value = (
                FakeUpstream(
                    [
                        {"type": "response.output_text.delta", "delta": "hello"},
                        {"type": "response.completed", "response": {"id": "resp-openai"}},
                    ]
                ),
                None,
            )

            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-5.3-codex", "messages": [{"role": "user", "content": "hi"}]},
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_start.call_args.kwargs["instructions"], "base only")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_accepts_standard_reasoning_effort(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.4",
                "reasoning_effort": "low",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["reasoning_param"]["effort"], "low")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_standard_reasoning_effort_overrides_nested_reasoning(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.4",
                "reasoning_effort": "low",
                "reasoning": {"effort": "high", "summary": "detailed"},
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["reasoning_param"]["effort"], "low")
        self.assertEqual(mock_start.call_args.kwargs["reasoning_param"]["summary"], "detailed")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_reasoning_defaults_unchanged_without_explicit_reasoning_fields(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = self.client.post(
            "/v1/chat/completions",
            json={"model": "gpt-5.4", "messages": [{"role": "user", "content": "hi"}]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_start.call_args.kwargs["reasoning_param"],
            {"effort": "medium", "summary": "auto"},
        )

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = self.client.post(
            "/v1/chat/completions",
            json={"model": "gpt5.4-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["choices"][0]["message"]["content"], "hello")
        self.assertEqual(body["model"], "gpt5.4-mini")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_honors_debug_model_override(self, mock_start) -> None:
        app = create_app(debug_model="gpt-5.4")
        client = app.test_client()
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-5.3-codex", "messages": [{"role": "user", "content": "hi"}]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.args[0], "gpt-5.4")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_use_fallback_instructions_when_default_injection_disabled(self, mock_start) -> None:
        app = create_app(inject_default_instructions=False)
        client = app.test_client()
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )

        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-5.4", "messages": [{"role": "user", "content": "hi"}]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["instructions"], fallback_passthrough_instructions())

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_completions_use_fallback_instructions_when_default_injection_disabled(self, mock_start) -> None:
        app = create_app(inject_default_instructions=False)
        client = app.test_client()
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )

        response = client.post(
            "/v1/completions",
            json={"model": "gpt-5.4", "prompt": "hi"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["instructions"], fallback_passthrough_instructions())

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_preserve_explicit_instructions(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )

        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.4",
                "instructions": "chat instructions",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["instructions"], "chat instructions")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_completions_preserve_explicit_instructions(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )

        response = self.client.post(
            "/v1/completions",
            json={
                "model": "gpt-5.4",
                "instructions": "completion instructions",
                "prompt": "hi",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["instructions"], "completion instructions")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_retry_reuses_resolved_instructions(self, mock_start) -> None:
        app = create_app(inject_default_instructions=False)
        client = app.test_client()
        mock_start.side_effect = [
            (
                FakeUpstream(status_code=400, content=b'{"error": {"message": "tool reject"}}', text='tool reject'),
                None,
            ),
            (
                FakeUpstream(
                    [
                        {"type": "response.output_text.delta", "delta": "hello"},
                        {"type": "response.completed", "response": {"id": "resp-retry"}},
                    ]
                ),
                None,
            ),
        ]

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.4",
                "messages": [{"role": "user", "content": "hi"}],
                "responses_tools": [{"type": "web_search"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_count, 2)
        self.assertEqual(mock_start.call_args_list[1].kwargs["instructions"], fallback_passthrough_instructions())

    @patch("chatmock.routes_ollama.start_upstream_request")
    def test_ollama_chat(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed"},
                ]
            ),
            None,
        )
        response = self.client.post(
            "/api/chat",
            json={"model": "gpt-5.4", "messages": [{"role": "user", "content": "hi"}], "stream": False},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["message"]["content"], "hello")
        self.assertEqual(body["model"], "gpt-5.4")

    @patch("chatmock.routes_ollama.start_upstream_request")
    def test_ollama_chat_honors_debug_model_override(self, mock_start) -> None:
        app = create_app(debug_model="gpt-5.4")
        client = app.test_client()
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed"},
                ]
            ),
            None,
        )
        response = client.post(
            "/api/chat",
            json={"model": "gpt-5.3-codex", "messages": [{"role": "user", "content": "hi"}], "stream": False},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.args[0], "gpt-5.4")
        self.assertEqual(body["model"], "gpt-5.4")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_fast_mode_sets_priority_service_tier(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.4",
                "fast_mode": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_start.call_args.kwargs["service_tier"], "priority")

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_fast_mode_false_overrides_server_default(self, mock_start) -> None:
        app = create_app(fast_mode=True)
        client = app.test_client()
        mock_start.return_value = (
            FakeUpstream(
                [
                    {"type": "response.output_text.delta", "delta": "hello"},
                    {"type": "response.completed", "response": {"id": "resp-openai"}},
                ]
            ),
            None,
        )
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.4",
                "fast_mode": False,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(mock_start.call_args.kwargs["service_tier"])

    @patch("chatmock.routes_openai.start_upstream_request")
    def test_chat_completions_rejects_unsupported_explicit_fast_mode(self, mock_start) -> None:
        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.3-codex",
                "fast_mode": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("Fast mode is not supported", body["error"]["message"])
        mock_start.assert_not_called()

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_returns_completed_response_object(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {
                        "type": "response.created",
                        "response": {"id": "resp_123", "object": "response", "status": "in_progress"},
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_123",
                            "object": "response",
                            "status": "completed",
                            "output": [],
                        },
                    },
                ],
                headers={"Content-Type": "text/event-stream"},
            ),
            None,
        )
        response = self.client.post(
            "/v1/responses",
            json={"model": "gpt5.4-mini", "input": "hello"},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["id"], "resp_123")
        outbound_payload = mock_start.call_args.args[0]
        self.assertEqual(outbound_payload["model"], "gpt-5.4-mini")
        self.assertEqual(outbound_payload["store"], False)
        self.assertEqual(
            outbound_payload["input"],
            [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
        )
        self.assertEqual(outbound_payload["reasoning"]["effort"], "medium")
        self.assertIsInstance(outbound_payload["prompt_cache_key"], str)

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_honors_debug_model_override(self, mock_start) -> None:
        app = create_app(debug_model="gpt-5.4")
        client = app.test_client()
        mock_start.return_value = (
            FakeUpstream(
                [
                    {
                        "type": "response.created",
                        "response": {"id": "resp_debug", "object": "response", "status": "in_progress"},
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_debug",
                            "object": "response",
                            "status": "completed",
                            "output": [],
                        },
                    },
                ],
                headers={"Content-Type": "text/event-stream"},
            ),
            None,
        )
        response = client.post(
            "/v1/responses",
            json={"model": "gpt-5.3-codex", "input": "hello"},
        )
        self.assertEqual(response.status_code, 200)
        outbound_payload = mock_start.call_args.args[0]
        self.assertEqual(outbound_payload["model"], "gpt-5.4")

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_preserves_explicit_instructions(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {
                        "type": "response.created",
                        "response": {"id": "resp_explicit", "object": "response", "status": "in_progress"},
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_explicit",
                            "object": "response",
                            "status": "completed",
                            "output": [],
                        },
                    },
                ],
                headers={"Content-Type": "text/event-stream"},
            ),
            None,
        )

        response = self.client.post(
            "/v1/responses",
            json={"model": "gpt-5.4", "instructions": "custom instructions", "input": "hello"},
        )

        self.assertEqual(response.status_code, 200)
        outbound_payload = mock_start.call_args.args[0]
        self.assertEqual(outbound_payload["instructions"], "custom instructions")

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_strips_unsupported_max_output_tokens(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {
                        "type": "response.created",
                        "response": {"id": "resp_limit", "object": "response", "status": "in_progress"},
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_limit",
                            "object": "response",
                            "status": "completed",
                            "output": [],
                        },
                    },
                ],
                headers={"Content-Type": "text/event-stream"},
            ),
            None,
        )
        response = self.client.post(
            "/v1/responses",
            json={"model": "gpt-5.4", "input": "hello", "max_output_tokens": 20},
        )
        self.assertEqual(response.status_code, 200)
        outbound_payload = mock_start.call_args.args[0]
        self.assertNotIn("max_output_tokens", outbound_payload)

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_does_not_use_previous_response_id_for_http_follow_up(self, mock_start) -> None:
        mock_start.side_effect = [
            (
                FakeUpstream(
                    [
                        {
                            "type": "response.created",
                            "response": {"id": "resp_1", "object": "response", "status": "in_progress"},
                        },
                        {
                            "type": "response.output_item.done",
                            "item": {
                                "type": "message",
                                "role": "assistant",
                                "id": "msg_1",
                                "content": [{"type": "output_text", "text": "assistant output"}],
                            },
                        },
                        {
                            "type": "response.completed",
                            "response": {"id": "resp_1", "object": "response", "status": "completed", "output": []},
                        },
                    ],
                    headers={"Content-Type": "text/event-stream"},
                ),
                None,
            ),
            (
                FakeUpstream(
                    [
                        {
                            "type": "response.created",
                            "response": {"id": "resp_2", "object": "response", "status": "in_progress"},
                        },
                        {
                            "type": "response.completed",
                            "response": {"id": "resp_2", "object": "response", "status": "completed", "output": []},
                        },
                    ],
                    headers={"Content-Type": "text/event-stream"},
                ),
                None,
            ),
        ]

        first = self.client.post("/v1/responses", json={"model": "gpt-5.4", "input": "hello"})
        second = self.client.post(
            "/v1/responses",
            json={
                "model": "gpt-5.4",
                "input": [
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                    {"type": "message", "role": "assistant", "id": "msg_1", "content": [{"type": "output_text", "text": "assistant output"}]},
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
                ],
            },
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        outbound_payload = mock_start.call_args_list[1].args[0]
        self.assertNotIn("previous_response_id", outbound_payload)
        self.assertEqual(
            outbound_payload["input"],
            [
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                {"type": "message", "role": "assistant", "id": "msg_1", "content": [{"type": "output_text", "text": "assistant output"}]},
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
            ],
        )

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_falls_back_to_full_create_when_non_input_fields_change(self, mock_start) -> None:
        mock_start.side_effect = [
            (
                FakeUpstream(
                    [
                        {
                            "type": "response.created",
                            "response": {"id": "resp_1", "object": "response", "status": "in_progress"},
                        },
                        {
                            "type": "response.completed",
                            "response": {"id": "resp_1", "object": "response", "status": "completed", "output": []},
                        },
                    ],
                    headers={"Content-Type": "text/event-stream"},
                ),
                None,
            ),
            (
                FakeUpstream(
                    [
                        {
                            "type": "response.created",
                            "response": {"id": "resp_2", "object": "response", "status": "in_progress"},
                        },
                        {
                            "type": "response.completed",
                            "response": {"id": "resp_2", "object": "response", "status": "completed", "output": []},
                        },
                    ],
                    headers={"Content-Type": "text/event-stream"},
                ),
                None,
            ),
        ]

        headers = {"X-Session-Id": "session-fixed"}
        first = self.client.post("/v1/responses", json={"model": "gpt-5.4", "input": "hello"}, headers=headers)
        second = self.client.post(
            "/v1/responses",
            json={
                "model": "gpt-5.4",
                "instructions": "changed",
                "input": [
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
                ],
            },
            headers=headers,
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        outbound_payload = mock_start.call_args_list[1].args[0]
        self.assertNotIn("previous_response_id", outbound_payload)
        self.assertEqual(
            outbound_payload["input"],
            [
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
            ],
        )

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_clears_reuse_state_after_error(self, mock_start) -> None:
        mock_start.side_effect = [
            (
                FakeUpstream(
                    [
                        {"type": "response.created", "response": {"id": "resp_1"}},
                        {"type": "response.completed", "response": {"id": "resp_1", "output": []}},
                    ],
                    headers={"Content-Type": "text/event-stream"},
                ),
                None,
            ),
            (
                FakeUpstream(
                    [
                        {"type": "response.failed", "response": {"error": {"message": "boom"}}},
                    ],
                    headers={"Content-Type": "text/event-stream"},
                ),
                None,
            ),
            (
                FakeUpstream(
                    [
                        {"type": "response.created", "response": {"id": "resp_3"}},
                        {"type": "response.completed", "response": {"id": "resp_3", "output": []}},
                    ],
                    headers={"Content-Type": "text/event-stream"},
                ),
                None,
            ),
        ]

        headers = {"X-Session-Id": "session-fixed"}
        first = self.client.post("/v1/responses", json={"model": "gpt-5.4", "input": "hello"}, headers=headers)
        second = self.client.post(
            "/v1/responses",
            json={
                "model": "gpt-5.4",
                "input": [
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
                ],
            },
            headers=headers,
        )
        third = self.client.post(
            "/v1/responses",
            json={
                "model": "gpt-5.4",
                "input": [
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "third"}]},
                ],
            },
            headers=headers,
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 502)
        self.assertEqual(third.status_code, 200)
        outbound_payload = mock_start.call_args_list[2].args[0]
        self.assertNotIn("previous_response_id", outbound_payload)
        self.assertEqual(
            outbound_payload["input"],
            [
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "third"}]},
            ],
        )

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_stream_passthrough(self, mock_start) -> None:
        chunk = b'data: {"type":"response.output_text.delta","delta":"hello"}\n\n'
        mock_start.return_value = (
            FakeUpstream(
                headers={"Content-Type": "text/event-stream"},
                content=chunk,
            ),
            None,
        )
        response = self.client.post(
            "/v1/responses",
            json={"model": "gpt-5.4", "input": "hello", "stream": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("response.output_text.delta", response.get_data(as_text=True))

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_stream_normalizes_tool_call_added_arguments(self, mock_start) -> None:
        tool_args = "{\"query\":\"today's weather in Kingston, Tennessee\",\"chatHistory\":[]}"
        mock_start.return_value = (
            FakeUpstream(
                [
                    {
                        "type": "response.created",
                        "response": {"id": "resp_tool", "object": "response", "status": "in_progress"},
                    },
                    {
                        "type": "response.output_item.added",
                        "item": {
                            "id": "fc_tool_1",
                            "type": "function_call",
                            "status": "in_progress",
                            "arguments": "",
                            "call_id": "call_tool_1",
                            "name": "webSearch",
                        },
                    },
                    {
                        "type": "response.function_call_arguments.delta",
                        "delta": tool_args,
                        "item_id": "fc_tool_1",
                        "output_index": 0,
                    },
                    {
                        "type": "response.function_call_arguments.done",
                        "arguments": "",
                        "item_id": "fc_tool_1",
                        "output_index": 0,
                    },
                    {
                        "type": "response.output_item.done",
                        "item": {
                            "id": "fc_tool_1",
                            "type": "function_call",
                            "status": "completed",
                            "arguments": "",
                            "call_id": "call_tool_1",
                            "name": "webSearch",
                        },
                    },
                    {
                        "type": "response.completed",
                        "response": {"id": "resp_tool", "object": "response", "status": "completed", "output": []},
                    },
                ],
                headers={"Content-Type": "text/event-stream"},
            ),
            None,
        )

        response = self.client.post(
            "/v1/responses",
            json={"model": "gpt-5.4", "input": "hello", "stream": True},
        )

        self.assertEqual(response.status_code, 200)
        events = decode_sse_events(response.get_data(as_text=True))
        self.assertEqual(events[0]["type"], "response.created")
        self.assertEqual(events[1]["type"], "response.output_item.added")
        self.assertEqual(events[1]["item"]["arguments"], tool_args)
        self.assertEqual(events[2]["type"], "response.function_call_arguments.done")
        self.assertEqual(events[2]["arguments"], tool_args)
        self.assertEqual(events[3]["type"], "response.output_item.done")
        self.assertEqual(events[3]["item"]["arguments"], tool_args)
        self.assertEqual(events[4]["type"], "response.completed")

    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_rejects_unsupported_explicit_priority(self, mock_start) -> None:
        response = self.client.post(
            "/v1/responses",
            json={"model": "gpt-5.3-codex", "input": "hello", "service_tier": "priority"},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("Fast mode is not supported", body["error"]["message"])
        mock_start.assert_not_called()

    @patch("chatmock.websocket_routes.get_effective_chatgpt_auth", return_value=("token", "acct"))
    @patch("chatmock.websocket_routes.connect_upstream_websocket")
    def test_responses_websocket_rewrites_response_create(self, mock_connect, _mock_auth) -> None:
        class FakeUpstreamWebsocket:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._messages = [
                    json.dumps({"type": "response.created", "response": {"id": "resp_ws_1"}}),
                    json.dumps({
                        "type": "response.output_item.done",
                        "item": {
                            "type": "message",
                            "role": "assistant",
                            "id": "msg_1",
                            "content": [{"type": "output_text", "text": "assistant output"}],
                        },
                    }),
                    json.dumps({"type": "response.completed", "response": {"id": "resp_ws_1"}}),
                    json.dumps({"type": "response.created", "response": {"id": "resp_ws_2"}}),
                    json.dumps({"type": "response.completed", "response": {"id": "resp_ws_2"}}),
                ]

            def send(self, message: str) -> None:
                self.sent.append(message)

            def recv(self) -> str:
                return self._messages.pop(0)

            def close(self) -> None:
                return None

        fake_upstream = FakeUpstreamWebsocket()
        mock_connect.return_value = fake_upstream

        app = create_app()

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()

        server_thread = threading.Thread(
            target=app.run,
            kwargs={
                "host": host,
                "port": port,
                "use_reloader": False,
                "threaded": True,
            },
            daemon=True,
        )
        server_thread.start()
        time.sleep(0.5)

        with ws_connect(f"ws://{host}:{port}/v1/responses") as client:
            client.send(json.dumps({"type": "response.create", "model": "gpt-5.4", "input": "hello", "fast_mode": True}))
            first = json.loads(client.recv())
            assistant = json.loads(client.recv())
            second = json.loads(client.recv())
            client.send(
                json.dumps(
                    {
                        "type": "response.create",
                        "model": "gpt-5.4",
                        "fast_mode": True,
                        "input": [
                            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                            {"type": "message", "role": "assistant", "id": "msg_1", "content": [{"type": "output_text", "text": "assistant output"}]},
                            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
                        ],
                    }
                )
            )
            third = json.loads(client.recv())
            fourth = json.loads(client.recv())

        self.assertEqual(first["type"], "response.created")
        self.assertEqual(assistant["type"], "response.output_item.done")
        self.assertEqual(second["type"], "response.completed")
        self.assertEqual(third["type"], "response.created")
        self.assertEqual(fourth["type"], "response.completed")
        outbound = json.loads(fake_upstream.sent[0])
        self.assertEqual(outbound["model"], "gpt-5.4")
        self.assertEqual(outbound["service_tier"], "priority")
        self.assertEqual(outbound["type"], "response.create")
        self.assertEqual(
            outbound["input"],
            [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
        )
        self.assertIn("prompt_cache_key", outbound)
        follow_up = json.loads(fake_upstream.sent[1])
        self.assertEqual(follow_up["previous_response_id"], "resp_ws_1")
        self.assertEqual(
            follow_up["input"],
            [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]}],
        )

    @patch("chatmock.websocket_routes.get_effective_chatgpt_auth", return_value=("token", "acct"))
    @patch("chatmock.websocket_routes.connect_upstream_websocket")
    def test_responses_websocket_normalizes_tool_call_added_arguments(self, mock_connect, _mock_auth) -> None:
        tool_args = "{\"path\":\"hello-2026-04-15.md\",\"content\":\"hello\"}"

        class FakeUpstreamWebsocket:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._messages = [
                    json.dumps({"type": "response.created", "response": {"id": "resp_ws_tool"}}),
                    json.dumps(
                        {
                            "type": "response.output_item.added",
                            "item": {
                                "id": "fc_ws_tool_1",
                                "type": "function_call",
                                "status": "in_progress",
                                "arguments": "",
                                "call_id": "call_ws_tool_1",
                                "name": "writeFile",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "response.function_call_arguments.delta",
                            "delta": tool_args,
                            "item_id": "fc_ws_tool_1",
                            "output_index": 0,
                        }
                    ),
                    json.dumps(
                        {
                            "type": "response.function_call_arguments.done",
                            "arguments": "",
                            "item_id": "fc_ws_tool_1",
                            "output_index": 0,
                        }
                    ),
                    json.dumps(
                        {
                            "type": "response.output_item.done",
                            "item": {
                                "id": "fc_ws_tool_1",
                                "type": "function_call",
                                "status": "completed",
                                "arguments": "",
                                "call_id": "call_ws_tool_1",
                                "name": "writeFile",
                            },
                        }
                    ),
                    json.dumps({"type": "response.completed", "response": {"id": "resp_ws_tool"}}),
                ]

            def send(self, message: str) -> None:
                self.sent.append(message)

            def recv(self) -> str:
                return self._messages.pop(0)

            def close(self) -> None:
                return None

        fake_upstream = FakeUpstreamWebsocket()
        mock_connect.return_value = fake_upstream

        app = create_app()

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()

        server_thread = threading.Thread(
            target=app.run,
            kwargs={
                "host": host,
                "port": port,
                "use_reloader": False,
                "threaded": True,
            },
            daemon=True,
        )
        server_thread.start()
        time.sleep(0.5)

        with ws_connect(f"ws://{host}:{port}/v1/responses") as client:
            client.send(json.dumps({"type": "response.create", "model": "gpt-5.4", "input": "hello"}))
            created = json.loads(client.recv())
            added = json.loads(client.recv())
            args_done = json.loads(client.recv())
            item_done = json.loads(client.recv())
            completed = json.loads(client.recv())

        self.assertEqual(created["type"], "response.created")
        self.assertEqual(added["type"], "response.output_item.added")
        self.assertEqual(added["item"]["arguments"], tool_args)
        self.assertEqual(args_done["type"], "response.function_call_arguments.done")
        self.assertEqual(args_done["arguments"], tool_args)
        self.assertEqual(item_done["type"], "response.output_item.done")
        self.assertEqual(item_done["item"]["arguments"], tool_args)
        self.assertEqual(completed["type"], "response.completed")

    @patch("chatmock.websocket_routes.get_effective_chatgpt_auth", return_value=("token", "acct"))
    @patch("chatmock.websocket_routes.connect_upstream_websocket")
    def test_responses_websocket_flushes_buffered_tool_call_before_unexpected_close(self, mock_connect, _mock_auth) -> None:
        tool_args = "{\"path\":\"flush-before-close.md\",\"content\":\"hello\"}"

        class FakeUpstreamWebsocket:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._messages = [
                    json.dumps({"type": "response.created", "response": {"id": "resp_ws_flush"}}),
                    json.dumps(
                        {
                            "type": "response.output_item.added",
                            "item": {
                                "id": "fc_ws_flush_1",
                                "type": "function_call",
                                "status": "in_progress",
                                "arguments": "",
                                "call_id": "call_ws_flush_1",
                                "name": "writeFile",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "response.function_call_arguments.delta",
                            "delta": tool_args,
                            "item_id": "fc_ws_flush_1",
                            "output_index": 0,
                        }
                    ),
                ]

            def send(self, message: str) -> None:
                self.sent.append(message)

            def recv(self) -> str:
                if self._messages:
                    return self._messages.pop(0)
                return None

            def close(self) -> None:
                return None

        fake_upstream = FakeUpstreamWebsocket()
        mock_connect.return_value = fake_upstream

        app = create_app()

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()

        server_thread = threading.Thread(
            target=app.run,
            kwargs={
                "host": host,
                "port": port,
                "use_reloader": False,
                "threaded": True,
            },
            daemon=True,
        )
        server_thread.start()
        time.sleep(0.5)

        with ws_connect(f"ws://{host}:{port}/v1/responses") as client:
            client.send(json.dumps({"type": "response.create", "model": "gpt-5.4", "input": "hello"}))
            created = json.loads(client.recv())
            added = json.loads(client.recv())
            error = json.loads(client.recv())

        self.assertEqual(created["type"], "response.created")
        self.assertEqual(added["type"], "response.output_item.added")
        self.assertEqual(added["item"]["arguments"], tool_args)
        self.assertEqual(error["type"], "error")
        self.assertIn("closed unexpectedly", error["error"]["message"])

    def test_iter_normalized_response_events_buffers_web_search_preview_call(self) -> None:
        tool_args = "{\"query\":\"preview me\"}"
        events = list(
            iter_normalized_response_events(
                [
                    {
                        "type": "response.output_item.added",
                        "item": {
                            "id": "fc_preview_1",
                            "type": "web_search_preview_call",
                            "status": "in_progress",
                            "arguments": "",
                            "call_id": "call_preview_1",
                            "name": "webSearchPreview",
                        },
                    },
                    {
                        "type": "response.function_call_arguments.delta",
                        "delta": tool_args,
                        "item_id": "fc_preview_1",
                        "output_index": 0,
                    },
                    {
                        "type": "response.function_call_arguments.done",
                        "arguments": "",
                        "item_id": "fc_preview_1",
                        "output_index": 0,
                    },
                    {
                        "type": "response.output_item.done",
                        "item": {
                            "id": "fc_preview_1",
                            "type": "web_search_preview_call",
                            "status": "completed",
                            "arguments": "",
                            "call_id": "call_preview_1",
                            "name": "webSearchPreview",
                        },
                    },
                ]
            )
        )

        self.assertEqual([event["type"] for event in events], [
            "response.output_item.added",
            "response.function_call_arguments.done",
            "response.output_item.done",
        ])
        self.assertEqual(events[0]["item"]["arguments"], tool_args)
        self.assertEqual(events[1]["arguments"], tool_args)
        self.assertEqual(events[2]["item"]["arguments"], tool_args)

    def test_iter_normalized_response_events_prefers_buffered_arguments_over_empty_structured_values(self) -> None:
        tool_args = "{\"query\":\"from-buffer\"}"
        events = list(
            iter_normalized_response_events(
                [
                    {
                        "type": "response.output_item.added",
                        "item": {
                            "id": "fc_buffer_1",
                            "type": "function_call",
                            "status": "in_progress",
                            "arguments": "",
                            "call_id": "call_buffer_1",
                            "name": "webSearch",
                        },
                    },
                    {
                        "type": "response.function_call_arguments.delta",
                        "delta": tool_args,
                        "item_id": "fc_buffer_1",
                        "output_index": 0,
                    },
                    {
                        "type": "response.function_call_arguments.done",
                        "arguments": {},
                        "item_id": "fc_buffer_1",
                        "output_index": 0,
                    },
                    {
                        "type": "response.output_item.done",
                        "item": {
                            "id": "fc_buffer_1",
                            "type": "function_call",
                            "status": "completed",
                            "arguments": {},
                            "call_id": "call_buffer_1",
                            "name": "webSearch",
                        },
                    },
                ]
            )
        )

        self.assertEqual(events[0]["item"]["arguments"], tool_args)
        self.assertEqual(events[1]["arguments"], tool_args)
        self.assertEqual(events[2]["item"]["arguments"], tool_args)

    def test_stream_upstream_bytes_preserves_done_sentinel(self) -> None:
        upstream = FakeUpstream(
            content=(
                b"data: {\"type\":\"response.created\",\"response\":{\"id\":\"resp_done\"}}\n\n"
                b"data: {\"type\":\"response.completed\",\"response\":{\"id\":\"resp_done\"}}\n\n"
                b"data: [DONE]\n\n"
            )
        )

        body = b"".join(stream_upstream_bytes(upstream)).decode("utf-8")
        events = decode_sse_events(body)

        self.assertEqual(events[0]["type"], "response.created")
        self.assertEqual(events[0]["response"]["id"], "resp_done")
        self.assertEqual(events[1]["type"], "response.completed")
        self.assertEqual(events[1]["response"]["id"], "resp_done")
        self.assertTrue(body.endswith("data: [DONE]\n\n"))

    def test_stream_upstream_bytes_preserves_raw_non_json_sse_frames(self) -> None:
        upstream = FakeUpstream(
            content=(
                b": keepalive\n\n"
                b"event: custom\ndata: plain-text-payload\n\n"
                b"data: {\"type\":\"response.completed\",\"response\":{\"id\":\"resp_raw\"}}\n\n"
                b"data: [DONE]\n\n"
            )
        )

        body = b"".join(stream_upstream_bytes(upstream)).decode("utf-8")
        events = decode_sse_events(body)

        self.assertIn(": keepalive\n\n", body)
        self.assertIn("event: custom\ndata: plain-text-payload\n\n", body)
        self.assertEqual(events[0]["type"], "response.completed")
        self.assertEqual(events[0]["response"]["id"], "resp_raw")
        self.assertTrue(body.endswith("data: [DONE]\n\n"))

    def test_stream_upstream_bytes_flushes_buffered_tool_call_before_done(self) -> None:
        tool_args = "{\"query\":\"flush-before-done\"}"
        upstream = FakeUpstream(
            content=(
                b"data: {\"type\":\"response.output_item.added\",\"item\":{\"id\":\"fc_done_1\",\"type\":\"function_call\",\"status\":\"in_progress\",\"arguments\":\"\",\"call_id\":\"call_done_1\",\"name\":\"webSearch\"}}\n\n"
                + f"data: {json.dumps({'type': 'response.function_call_arguments.delta', 'delta': tool_args, 'item_id': 'fc_done_1', 'output_index': 0})}\n\n".encode("utf-8")
                + b"data: [DONE]\n\n"
            )
        )

        body = b"".join(stream_upstream_bytes(upstream)).decode("utf-8")
        events = decode_sse_events(body)

        self.assertEqual(events[0]["type"], "response.output_item.added")
        self.assertEqual(events[0]["item"]["arguments"], tool_args)
        self.assertTrue(body.endswith("data: [DONE]\n\n"))
        self.assertEqual(len(events), 1)

    def test_iter_sse_frames_handles_crlf_delimiter_split_across_chunks(self) -> None:
        class ChunkedUpstream(FakeUpstream):
            def __init__(self, chunks: list[bytes]) -> None:
                super().__init__(events=[])
                self._chunks = chunks

            def iter_content(self, chunk_size=None):
                for chunk in self._chunks:
                    yield chunk

        upstream = ChunkedUpstream(
            [
                b'data: {"type":"response.created","response":{"id":"resp_crlf"}}\r\n\r',
                b'\ndata: {"type":"response.completed","response":{"id":"resp_crlf"}}\r\n\r\n',
                b'data: [DONE]\r\n\r\n',
            ]
        )

        body = b"".join(stream_upstream_bytes(upstream)).decode("utf-8")
        events = decode_sse_events(body)

        self.assertEqual([event["type"] for event in events], ["response.created", "response.completed"])
        self.assertTrue(body.endswith("data: [DONE]\r\n\r\n") or body.endswith("data: [DONE]\n\n"))

    def test_iter_sse_frames_handles_mixed_blank_line_delimiters(self) -> None:
        class ChunkedUpstream(FakeUpstream):
            def __init__(self, chunks: list[bytes]) -> None:
                super().__init__(events=[])
                self._chunks = chunks

            def iter_content(self, chunk_size=None):
                for chunk in self._chunks:
                    yield chunk

        upstream = ChunkedUpstream(
            [
                b'data: {"type":"response.created","response":{"id":"resp_mixed"}}\n\r\n',
                b'data: {"type":"response.completed","response":{"id":"resp_mixed"}}\r\n\n',
                b'data: [DONE]\n\n',
            ]
        )

        body = b"".join(stream_upstream_bytes(upstream)).decode("utf-8")
        events = decode_sse_events(body)

        self.assertEqual([event["type"] for event in events], ["response.created", "response.completed"])
        self.assertTrue(body.endswith("data: [DONE]\n\n"))

    def test_iter_normalized_response_events_normalizes_terminal_response_output_arguments(self) -> None:
        tool_args = "{\"query\":\"from-terminal-output\"}"
        events = list(
            iter_normalized_response_events(
                [
                    {
                        "type": "response.output_item.added",
                        "item": {
                            "id": "fc_terminal_1",
                            "type": "function_call",
                            "status": "in_progress",
                            "arguments": "",
                            "call_id": "call_terminal_1",
                            "name": "webSearch",
                        },
                    },
                    {
                        "type": "response.function_call_arguments.delta",
                        "delta": tool_args,
                        "item_id": "fc_terminal_1",
                        "output_index": 0,
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_terminal",
                            "output": [
                                {
                                    "id": "fc_terminal_1",
                                    "type": "function_call",
                                    "status": "completed",
                                    "arguments": "",
                                    "call_id": "call_terminal_1",
                                    "name": "webSearch",
                                }
                            ],
                        },
                    },
                ]
            )
        )

        self.assertEqual(events[0]["type"], "response.output_item.added")
        self.assertEqual(events[0]["item"]["arguments"], tool_args)
        self.assertEqual(events[1]["type"], "response.completed")
        self.assertEqual(events[1]["response"]["output"][0]["arguments"], tool_args)

    def test_iter_normalized_response_events_keeps_pending_state_for_completed_after_item_done(self) -> None:
        tool_args = "{\"query\":\"from-output-item-done\"}"
        events = list(
            iter_normalized_response_events(
                [
                    {
                        "type": "response.output_item.added",
                        "item": {
                            "id": "fc_terminal_2",
                            "type": "function_call",
                            "status": "in_progress",
                            "arguments": "",
                            "call_id": "call_terminal_2",
                            "name": "webSearch",
                        },
                    },
                    {
                        "type": "response.function_call_arguments.delta",
                        "delta": tool_args,
                        "item_id": "fc_terminal_2",
                        "output_index": 0,
                    },
                    {
                        "type": "response.output_item.done",
                        "item": {
                            "id": "fc_terminal_2",
                            "type": "function_call",
                            "status": "completed",
                            "arguments": "",
                            "call_id": "call_terminal_2",
                            "name": "webSearch",
                        },
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_terminal_2",
                            "output": [
                                {
                                    "id": "fc_terminal_2",
                                    "type": "function_call",
                                    "status": "completed",
                                    "arguments": "",
                                    "call_id": "call_terminal_2",
                                    "name": "webSearch",
                                }
                            ],
                        },
                    },
                ]
            )
        )

        self.assertEqual(events[0]["type"], "response.output_item.added")
        self.assertEqual(events[0]["item"]["arguments"], tool_args)
        self.assertEqual(events[1]["type"], "response.output_item.done")
        self.assertEqual(events[1]["item"]["arguments"], tool_args)
        self.assertEqual(events[2]["type"], "response.completed")
        self.assertEqual(events[2]["response"]["output"][0]["arguments"], tool_args)

    def test_iter_normalized_response_events_flushes_before_done_and_stops(self) -> None:
        tool_args = "{\"query\":\"done-stop\"}"
        events = list(
            iter_normalized_response_events(
                [
                    {
                        "type": "response.output_item.added",
                        "item": {
                            "id": "fc_done_stop_1",
                            "type": "function_call",
                            "status": "in_progress",
                            "arguments": "",
                            "call_id": "call_done_stop_1",
                            "name": "webSearch",
                        },
                    },
                    {
                        "type": "response.function_call_arguments.delta",
                        "delta": tool_args,
                        "item_id": "fc_done_stop_1",
                        "output_index": 0,
                    },
                    {"type": "[DONE]", "data": "[DONE]"},
                    {
                        "type": "response.output_text.delta",
                        "delta": "should-not-be-emitted",
                    },
                ]
            )
        )

        self.assertEqual(events[0]["type"], "response.output_item.added")
        self.assertEqual(events[0]["item"]["arguments"], tool_args)
        self.assertEqual(events[1]["type"], "[DONE]")
        self.assertEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
