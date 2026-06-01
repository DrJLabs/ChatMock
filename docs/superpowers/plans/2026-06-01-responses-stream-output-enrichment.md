# Responses Stream Output Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every ChatMock streaming Responses terminal event includes a populated `response.output` and `response.output_text` when output was emitted earlier in the same stream.

**Architecture:** Add a shared stream-output accumulator in `chatmock/responses_api.py` that observes normalized stream events and enriches `response.completed` before the event leaves ChatMock. Use the same accumulator for HTTP SSE streaming, WebSocket streaming, and non-streaming SSE aggregation so all Responses paths preserve the same final-response contract.

**Tech Stack:** Python 3.11+, Flask, Flask-Sock, Server-Sent Events, WebSocket, `unittest`, pytest.

---

## Current Failure

Live streaming `/v1/responses` already emits `response.output_item.done` events with message content, but the later `response.completed.response` lacks both `output` and `output_text`. Clients that read `response.output` from the terminal event crash with:

```text
undefined is not an object (evaluating 't.output')
```

The non-streaming `/v1/responses` path does not have this bug because `aggregate_response_from_sse()` calls `_populate_response_output_from_stream()`.

## File Structure

- Modify: `chatmock/responses_api.py`
  - Add `ResponsesStreamOutputAccumulator`.
  - Reuse it in `aggregate_response_from_sse()`.
  - Use it inside `stream_upstream_bytes()` before emitting terminal `response.completed` events.

- Modify: `chatmock/websocket_routes.py`
  - Import `ResponsesStreamOutputAccumulator`.
  - Create one accumulator per upstream response stream.
  - Enrich each normalized event before sending it to the client and before recording session state.

- Modify: `tests/test_routes.py`
  - Add failing HTTP SSE regression coverage for `stream_upstream_bytes()`.
  - Add failing route-level regression coverage for `POST /v1/responses` with `stream: true`.
  - Add failing WebSocket regression coverage for `response.completed.response.output`.

## Contract

For a stream containing:

```json
{"type":"response.output_item.done","item":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"assistant output"}]}}
{"type":"response.completed","response":{"id":"resp_1","status":"completed"}}
```

ChatMock must emit the terminal event as:

```json
{
  "type": "response.completed",
  "response": {
    "id": "resp_1",
    "status": "completed",
    "output": [
      {
        "type": "message",
        "role": "assistant",
        "content": [
          {"type": "output_text", "text": "assistant output"}
        ]
      }
    ],
    "output_text": "assistant output"
  }
}
```

If upstream already sends a non-empty `response.output`, preserve that output and fill `output_text` from it when missing.

If upstream sends text deltas or text-done events but no output item, synthesize a completed assistant message using the existing `_populate_response_output_from_stream()` behavior.

If no output was emitted, leave the terminal response unchanged.

---

### Task 1: Add HTTP SSE Regression Tests

**Files:**
- Modify: `tests/test_routes.py`
- Test: `tests/test_routes.py::RouteTests::test_stream_upstream_bytes_enriches_completed_response_from_output_items`
- Test: `tests/test_routes.py::RouteTests::test_stream_upstream_bytes_synthesizes_output_from_text_delta`
- Test: `tests/test_routes.py::RouteTests::test_responses_route_stream_enriches_completed_response_output`

- [ ] **Step 1: Add stream helper tests**

Insert these tests in `tests/test_routes.py` after `test_stream_upstream_bytes_preserves_raw_non_json_sse_frames` and before `test_stream_upstream_bytes_flushes_buffered_tool_call_before_done`.

```python
    def test_stream_upstream_bytes_enriches_completed_response_from_output_items(self) -> None:
        upstream = FakeUpstream(
            [
                {
                    "type": "response.created",
                    "response": {"id": "resp_stream_output", "object": "response", "status": "in_progress"},
                },
                {
                    "type": "response.output_item.done",
                    "item": {
                        "id": "msg_stream_output",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "assistant output"}],
                    },
                },
                {
                    "type": "response.completed",
                    "response": {"id": "resp_stream_output", "object": "response", "status": "completed"},
                },
            ],
            headers={"Content-Type": "text/event-stream"},
        )

        body = b"".join(stream_upstream_bytes(upstream)).decode("utf-8")
        events = decode_sse_events(body)

        self.assertEqual(events[-1]["type"], "response.completed")
        completed_response = events[-1]["response"]
        self.assertEqual(
            completed_response["output"],
            [
                {
                    "id": "msg_stream_output",
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "assistant output"}],
                }
            ],
        )
        self.assertEqual(completed_response["output_text"], "assistant output")

    def test_stream_upstream_bytes_synthesizes_output_from_text_delta(self) -> None:
        upstream = FakeUpstream(
            [
                {
                    "type": "response.created",
                    "response": {"id": "resp_stream_delta", "object": "response", "status": "in_progress"},
                },
                {
                    "type": "response.output_text.delta",
                    "delta": "hello ",
                    "item_id": "msg_stream_delta",
                    "output_index": 0,
                    "content_index": 0,
                },
                {
                    "type": "response.output_text.done",
                    "text": "hello world",
                    "item_id": "msg_stream_delta",
                    "output_index": 0,
                    "content_index": 0,
                },
                {
                    "type": "response.completed",
                    "response": {"id": "resp_stream_delta", "object": "response", "status": "completed"},
                },
            ],
            headers={"Content-Type": "text/event-stream"},
        )

        body = b"".join(stream_upstream_bytes(upstream)).decode("utf-8")
        events = decode_sse_events(body)

        completed_response = events[-1]["response"]
        self.assertEqual(completed_response["output_text"], "hello ")
        self.assertEqual(
            completed_response["output"],
            [
                {
                    "id": "msg_resp_stream_delta",
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "hello "}],
                }
            ],
        )
```

- [ ] **Step 2: Add route-level streaming test**

Insert this test in `tests/test_routes.py` after `test_responses_route_stream_normalizes_tool_call_added_arguments`.

```python
    @patch("chatmock.routes_openai.start_upstream_raw_request")
    def test_responses_route_stream_enriches_completed_response_output(self, mock_start) -> None:
        mock_start.return_value = (
            FakeUpstream(
                [
                    {
                        "type": "response.created",
                        "response": {
                            "id": "resp_route_stream_output",
                            "object": "response",
                            "status": "in_progress",
                        },
                    },
                    {
                        "type": "response.output_item.done",
                        "item": {
                            "id": "msg_route_stream_output",
                            "type": "message",
                            "status": "completed",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "route assistant output"}],
                        },
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_route_stream_output",
                            "object": "response",
                            "status": "completed",
                        },
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
        completed_response = events[-1]["response"]
        self.assertEqual(completed_response["output_text"], "route assistant output")
        self.assertEqual(
            completed_response["output"],
            [
                {
                    "id": "msg_route_stream_output",
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "route assistant output"}],
                }
            ],
        )
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_routes.py -k "stream_upstream_bytes_enriches_completed_response_from_output_items or stream_upstream_bytes_synthesizes_output_from_text_delta or responses_route_stream_enriches_completed_response_output" -q
```

Expected result before implementation:

```text
FAILED tests/test_routes.py::RouteTests::test_stream_upstream_bytes_enriches_completed_response_from_output_items
FAILED tests/test_routes.py::RouteTests::test_stream_upstream_bytes_synthesizes_output_from_text_delta
FAILED tests/test_routes.py::RouteTests::test_responses_route_stream_enriches_completed_response_output
```

The failures should be `KeyError: 'output'` or `KeyError: 'output_text'` on the completed response.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/test_routes.py
git commit -m "test(responses): cover streaming completed output enrichment"
```

---

### Task 2: Add Shared Stream Output Accumulator

**Files:**
- Modify: `chatmock/responses_api.py`
- Test: `tests/test_routes.py::RouteTests::test_stream_upstream_bytes_enriches_completed_response_from_output_items`
- Test: `tests/test_routes.py::RouteTests::test_stream_upstream_bytes_synthesizes_output_from_text_delta`
- Test: `tests/test_routes.py::RouteTests::test_responses_route_stream_enriches_completed_response_output`

- [ ] **Step 1: Add accumulator class**

In `chatmock/responses_api.py`, insert this class after `_response_output_text()`.

```python
class ResponsesStreamOutputAccumulator:
    def __init__(self) -> None:
        self._output_items: List[Dict[str, Any]] = []
        self._output_text_parts: List[str] = []
        self._output_text_delta_keys: set[tuple[Any, Any, Any]] = set()
        self._unkeyed_delta_parts: List[str] = []

    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        kind = event.get("type")
        if kind == "response.completed":
            return self._enrich_completed_event(event)
        if kind == "response.output_text.delta":
            self._record_output_text_delta(event)
        elif kind == "response.output_text.done":
            self._record_output_text_done(event)
        elif kind == "response.output_item.done":
            item = event.get("item")
            if isinstance(item, dict):
                self._output_items.append(copy.deepcopy(item))
        return event

    def _record_output_text_delta(self, event: Dict[str, Any]) -> None:
        delta = event.get("delta")
        if not isinstance(delta, str) or not delta:
            return
        key = _output_text_event_key(event)
        if key is not None:
            self._output_text_delta_keys.add(key)
        else:
            self._unkeyed_delta_parts.append(delta)
        self._output_text_parts.append(delta)

    def _record_output_text_done(self, event: Dict[str, Any]) -> None:
        text = event.get("text")
        if not isinstance(text, str) or not text:
            return
        key = _output_text_event_key(event)
        if key is None:
            unkeyed_delta_text = "".join(self._unkeyed_delta_parts)
            if text != unkeyed_delta_text:
                self._output_text_parts.append(text)
            self._unkeyed_delta_parts = []
            return
        if key not in self._output_text_delta_keys:
            self._output_text_parts.append(text)

    def _enrich_completed_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        response = event.get("response")
        if not isinstance(response, dict):
            return event
        enriched = event.copy()
        enriched["response"] = _populate_response_output_from_stream(
            response,
            output_items=self._output_items,
            output_text="".join(self._output_text_parts),
        )
        return enriched
```

- [ ] **Step 2: Use accumulator in `aggregate_response_from_sse()`**

In `aggregate_response_from_sse()`, replace the local tracking variables:

```python
    output_items: List[Dict[str, Any]] = []
    output_text_parts: List[str] = []
    output_text_delta_keys: set[tuple[Any, Any, Any]] = set()
    unkeyed_delta_parts: List[str] = []
```

with:

```python
    output_accumulator = ResponsesStreamOutputAccumulator()
```

Then replace the event loop body from the current first `response = evt.get("response")` through the `response.failed` branch with this equivalent logic:

```python
            kind = evt.get("type")
            enriched_evt = output_accumulator.process(evt)
            response = enriched_evt.get("response")
            if isinstance(response, dict):
                response_obj = response
            if kind == "response.completed":
                completed_event = enriched_evt
                break
            if callable(on_event):
                try:
                    on_event(enriched_evt)
                except Exception:
                    pass
            if kind == "response.failed":
                if isinstance(response, dict) and isinstance(response.get("error"), dict):
                    error_obj = {"error": response.get("error")}
                else:
                    error_obj = {"error": {"message": "response.failed"}}
                break
```

Remove the old duplicate collection branches for `response.output_text.delta`, `response.output_text.done`, and `response.output_item.done`.

Then replace the post-loop population block:

```python
    if response_obj is not None:
        response_obj = _populate_response_output_from_stream(
            response_obj,
            output_items=output_items,
            output_text="".join(output_text_parts),
        )
```

with:

```python
    if completed_event is not None:
        completed_response = completed_event.get("response")
        if isinstance(completed_response, dict):
            response_obj = completed_response
```

- [ ] **Step 3: Use accumulator in `stream_upstream_bytes()`**

In `stream_upstream_bytes()`, after creating `normalizer`, create the accumulator:

```python
        normalizer = ResponsesToolCallStreamNormalizer()
        output_accumulator = ResponsesStreamOutputAccumulator()
```

Then, inside the `for normalized in normalizer.process(evt):` loop, replace the callback/yield block:

```python
                if callable(on_event):
                    try:
                        on_event(normalized)
                    except Exception:
                        pass
                event_type = normalized.get("type")
```

with:

```python
                normalized = output_accumulator.process(normalized)
                if callable(on_event):
                    try:
                        on_event(normalized)
                    except Exception:
                        pass
                event_type = normalized.get("type")
```

Then, inside the flush loop for the `[DONE]` branch, replace:

```python
                        if callable(on_event):
                            try:
                                on_event(flushed)
                            except Exception:
                                pass
                        payload = json.dumps(flushed, ensure_ascii=False)
```

with:

```python
                        flushed = output_accumulator.process(flushed)
                        if callable(on_event):
                            try:
                                on_event(flushed)
                            except Exception:
                                pass
                        payload = json.dumps(flushed, ensure_ascii=False)
```

Finally, in the end-of-stream flush loop, replace:

```python
            if callable(on_event):
                try:
                    on_event(normalized)
                except Exception:
                    pass
            payload = json.dumps(normalized, ensure_ascii=False)
```

with:

```python
            normalized = output_accumulator.process(normalized)
            if callable(on_event):
                try:
                    on_event(normalized)
                except Exception:
                    pass
            payload = json.dumps(normalized, ensure_ascii=False)
```

- [ ] **Step 4: Run HTTP streaming tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_routes.py -k "stream_upstream_bytes_enriches_completed_response_from_output_items or stream_upstream_bytes_synthesizes_output_from_text_delta or responses_route_stream_enriches_completed_response_output" -q
```

Expected result after implementation:

```text
3 passed
```

- [ ] **Step 5: Run existing Responses regression subset**

Run:

```bash
.venv/bin/python -m pytest tests/test_routes.py -k "responses_route_returns_completed_response_object or responses_route_populates_output_from_stream_text_when_completed_output_empty or responses_route_replaces_empty_output_text_from_stream_text or responses_route_appends_done_only_output_text_segments or aggregate_response_from_sse_emits_enriched_completed_event_to_callback or responses_route_stream_normalizes_tool_call_added_arguments or stream_upstream_bytes_preserves_done_sentinel or stream_upstream_bytes_preserves_raw_non_json_sse_frames or stream_upstream_bytes_flushes_buffered_tool_call_before_done or iter_normalized_response_events" -q
```

Expected result:

```text
passed
```

- [ ] **Step 6: Commit HTTP streaming implementation**

```bash
git add chatmock/responses_api.py tests/test_routes.py
git commit -m "fix(responses): enrich streaming completed output"
```

---

### Task 3: Add WebSocket Regression Test and Enrichment

**Files:**
- Modify: `tests/test_routes.py`
- Modify: `chatmock/websocket_routes.py`
- Test: `tests/test_routes.py::RouteTests::test_responses_websocket_enriches_completed_response_output`

- [ ] **Step 1: Add WebSocket failing test**

Insert this test in `tests/test_routes.py` after `test_responses_websocket_rewrites_response_create`.

```python
    @patch("chatmock.websocket_routes.get_effective_chatgpt_auth", return_value=("token", "acct"))
    @patch("chatmock.websocket_routes.connect_upstream_websocket")
    def test_responses_websocket_enriches_completed_response_output(self, mock_connect, _mock_auth) -> None:
        class FakeUpstreamWebsocket:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._messages = [
                    json.dumps({"type": "response.created", "response": {"id": "resp_ws_output"}}),
                    json.dumps(
                        {
                            "type": "response.output_item.done",
                            "item": {
                                "id": "msg_ws_output",
                                "type": "message",
                                "status": "completed",
                                "role": "assistant",
                                "content": [{"type": "output_text", "text": "websocket assistant output"}],
                            },
                        }
                    ),
                    json.dumps({"type": "response.completed", "response": {"id": "resp_ws_output", "status": "completed"}}),
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
            item_done = json.loads(client.recv())
            completed = json.loads(client.recv())

        self.assertEqual(created["type"], "response.created")
        self.assertEqual(item_done["type"], "response.output_item.done")
        self.assertEqual(completed["type"], "response.completed")
        completed_response = completed["response"]
        self.assertEqual(completed_response["output_text"], "websocket assistant output")
        self.assertEqual(
            completed_response["output"],
            [
                {
                    "id": "msg_ws_output",
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "websocket assistant output"}],
                }
            ],
        )
```

- [ ] **Step 2: Run WebSocket test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_routes.py::RouteTests::test_responses_websocket_enriches_completed_response_output -q
```

Expected result before implementation:

```text
FAILED tests/test_routes.py::RouteTests::test_responses_websocket_enriches_completed_response_output
```

The failure should be `KeyError: 'output_text'` or `KeyError: 'output'`.

- [ ] **Step 3: Import accumulator in WebSocket route**

In `chatmock/websocket_routes.py`, update the import block from `chatmock.responses_api` to include `ResponsesStreamOutputAccumulator`.

```python
from .responses_api import (
    ResponsesRequestError,
    ResponsesStreamOutputAccumulator,
    ResponsesToolCallStreamNormalizer,
    extract_client_session_id,
    normalize_responses_payload,
)
```

- [ ] **Step 4: Use accumulator in WebSocket response loop**

In `register_websocket_routes()`, immediately after:

```python
                stream_normalizer = ResponsesToolCallStreamNormalizer()
```

add:

```python
                output_accumulator = ResponsesStreamOutputAccumulator()
```

Then replace the normalized event send loop:

```python
                        for normalized_event in stream_normalizer.process(parsed):
                            normalized_message = json.dumps(normalized_event, ensure_ascii=False)
                            ws.send(normalized_message)
                            if active_session_id:
                                note_responses_stream_event(active_session_id, normalized_event)
                            if _is_terminal_event(normalized_event):
                                emitted_terminal = True
```

with:

```python
                        for normalized_event in stream_normalizer.process(parsed):
                            normalized_event = output_accumulator.process(normalized_event)
                            normalized_message = json.dumps(normalized_event, ensure_ascii=False)
                            ws.send(normalized_message)
                            if active_session_id:
                                note_responses_stream_event(active_session_id, normalized_event)
                            if _is_terminal_event(normalized_event):
                                emitted_terminal = True
```

- [ ] **Step 5: Enrich flushed WebSocket events**

Change `_flush_normalized_events()` to accept an optional output accumulator.

Replace the helper signature:

```python
        def _flush_normalized_events(
            stream_normalizer: ResponsesToolCallStreamNormalizer,
            *,
            session_id: str | None,
        ) -> None:
```

with:

```python
        def _flush_normalized_events(
            stream_normalizer: ResponsesToolCallStreamNormalizer,
            *,
            session_id: str | None,
            output_accumulator: ResponsesStreamOutputAccumulator | None = None,
        ) -> None:
```

Then replace the first line inside the loop:

```python
            for normalized_event in stream_normalizer.flush():
```

and the immediately following message creation with:

```python
            for normalized_event in stream_normalizer.flush():
                if output_accumulator is not None:
                    normalized_event = output_accumulator.process(normalized_event)
```

Keep the existing `normalized_message = json.dumps(...)`, `ws.send(...)`, and `note_responses_stream_event(...)` lines after that.

Finally, update both unexpected-close call sites inside the loop:

```python
                        _flush_normalized_events(stream_normalizer, session_id=active_session_id)
```

to:

```python
                        _flush_normalized_events(
                            stream_normalizer,
                            session_id=active_session_id,
                            output_accumulator=output_accumulator,
                        )
```

- [ ] **Step 6: Run WebSocket test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_routes.py::RouteTests::test_responses_websocket_enriches_completed_response_output -q
```

Expected result:

```text
1 passed
```

- [ ] **Step 7: Run WebSocket regression subset**

Run:

```bash
.venv/bin/python -m pytest tests/test_routes.py -k "responses_websocket_rewrites_response_create or responses_websocket_enriches_completed_response_output or responses_websocket_normalizes_tool_call_added_arguments or responses_websocket_flushes_buffered_tool_call_before_unexpected_close" -q
```

Expected result:

```text
passed
```

- [ ] **Step 8: Commit WebSocket implementation**

```bash
git add chatmock/websocket_routes.py tests/test_routes.py
git commit -m "fix(responses): enrich websocket completed output"
```

---

### Task 4: Full Verification and Live Smoke

**Files:**
- Verify only; no required file edits.

- [ ] **Step 1: Run backend Responses route suite**

Run:

```bash
.venv/bin/python -m pytest tests/test_routes.py -q
```

Expected result:

```text
passed
```

- [ ] **Step 2: Run admin route suite to catch app-level regressions**

Run:

```bash
.venv/bin/python -m pytest tests/test_admin_routes.py -q
```

Expected result:

```text
passed
```

- [ ] **Step 3: Build or restart the running stack**

If code is running from the checked-out source through Docker image `chatmock-local:dev`, rebuild before restart:

```bash
docker compose build chatmock chatmock-clawmem
docker compose up -d chatmock chatmock-clawmem
```

If the local image was already rebuilt by the implementation workflow, restart is enough:

```bash
docker compose restart chatmock chatmock-clawmem
```

Expected result:

```text
Container chatmock Started
Container chatmock-clawmem Started
```

- [ ] **Step 4: Confirm container health**

Run:

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8001/health
```

Expected results:

```text
chatmock           Up ... (healthy)
chatmock-clawmem   Up ... (healthy)
{"status":"ok"}
{"status":"ok"}
```

- [ ] **Step 5: Run live streaming contract smoke**

Run:

```bash
python3 - <<'PY'
import json
import urllib.request

request = urllib.request.Request(
    "http://127.0.0.1:8000/v1/responses",
    data=json.dumps(
        {
            "model": "gpt-5.3-codex-spark",
            "input": "Say ok.",
            "stream": True,
            "max_output_tokens": 50,
        }
    ).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

completed = None
with urllib.request.urlopen(request, timeout=90) as response:
    for raw_line in response:
        line = raw_line.decode("utf-8", "replace").strip()
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        event = json.loads(line[len("data: "):])
        if event.get("type") == "response.completed":
            completed = event
            break

if not isinstance(completed, dict):
    raise SystemExit("missing response.completed")
body = completed.get("response")
if not isinstance(body, dict):
    raise SystemExit("missing completed response object")
if not isinstance(body.get("output"), list):
    raise SystemExit("completed response.output is not a list")
if not body.get("output_text"):
    raise SystemExit("completed response.output_text is missing")
print("streaming completed output ok")
PY
```

Expected result:

```text
streaming completed output ok
```

- [ ] **Step 6: Confirm auth still works after restart**

Run:

```bash
docker compose exec -T chatmock chatmock info | sed -n '1,8p'
```

Expected result:

```text
👤 Account
  • Signed in with ChatGPT
```

- [ ] **Step 7: Commit verification notes if files changed after implementation**

If implementation generated no additional file changes, do not make a verification-only commit. If test snapshots or documentation were intentionally updated, commit them with:

```bash
git add <changed-files>
git commit -m "test(responses): verify streaming output contract"
```

---

## Self-Review

**Spec coverage:** The plan covers the live client crash by requiring final streaming `response.completed.response.output` and `response.completed.response.output_text` for HTTP SSE and WebSocket. It keeps non-streaming behavior covered by reusing the same enrichment mechanism in `aggregate_response_from_sse()`.

**Placeholder scan:** The plan contains exact files, test functions, implementation snippets, commands, expected failures, expected passes, and commit messages. It does not rely on undefined follow-up work.

**Type consistency:** The plan uses existing `Dict[str, Any]`, `List[...]`, `_output_text_event_key()`, `_populate_response_output_from_stream()`, `ResponsesToolCallStreamNormalizer`, `stream_upstream_bytes()`, and `note_responses_stream_event()` names exactly as they exist in the current codebase.

**Risk:** The largest behavior change is that streaming terminal events become richer. This is additive for clients and aligns streaming with non-streaming. Existing clients that ignore `response.output` continue to work.

## Execution Results

Completed on 2026-06-01.

- Task 1 commit: `97fd5c1` (`test(responses): cover streaming completed output enrichment`)
- Task 2 commit: `8bab8b9` (`fix(responses): enrich streaming completed output`)
- Task 3 commit: `d9dd011` (`fix(responses): enrich websocket completed output`)
- Task 3 also fixed the review-discovered accumulator lifecycle edge case by resetting stream-output state after each `response.completed`.

Verification:

- `.venv/bin/python -m pytest tests/test_routes.py -q` -> `71 passed, 2 warnings`
- `.venv/bin/python -m pytest tests/test_admin_routes.py -q` -> `21 passed`
- `docker build -t chatmock-local:dev .` -> passed
- `docker compose up -d chatmock chatmock-clawmem` -> both services restarted
- `docker compose ps` -> both services healthy
- `curl -fsS http://127.0.0.1:8000/health` -> `{"status":"ok"}`
- `curl -fsS http://127.0.0.1:8001/health` -> `{"status":"ok"}`
- Live streaming smoke against `http://127.0.0.1:8000/v1/responses` -> terminal `response.completed.response.output` is a list and `output_text` is present (`"Ok."`)
- `docker compose exec -T chatmock chatmock info` -> signed in with ChatGPT

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-06-01-responses-stream-output-enrichment.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.
