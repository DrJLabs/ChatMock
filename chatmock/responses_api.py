from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Literal

from .config import BASE_INSTRUCTIONS, GPT5_CODEX_INSTRUCTIONS
from .fast_mode import ServiceTierResolution, resolve_service_tier
from .model_registry import (
    allowed_efforts_for_model,
    extract_reasoning_from_model_name,
    normalize_model_name,
    uses_codex_instructions,
)
from .reasoning import build_reasoning_param
from .session import ensure_session_id


@dataclass(frozen=True)
class ResponsesRequestError(Exception):
    message: str
    status_code: int = 400
    code: str | None = None

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class NormalizedResponsesRequest:
    payload: Dict[str, Any]
    requested_model: str | None
    normalized_model: str
    session_id: str
    service_tier_resolution: ServiceTierResolution


def instructions_for_model(config: Dict[str, Any], model: str) -> str:
    prompt_manager = config.get("PROMPT_MANAGER")
    base = config.get("BASE_INSTRUCTIONS")
    if (not isinstance(base, str) or not base.strip()) and hasattr(prompt_manager, "get_base_instructions"):
        base = prompt_manager.get_base_instructions()
    if not isinstance(base, str) or not base.strip():
        base = BASE_INSTRUCTIONS
    if uses_codex_instructions(model):
        codex = config.get("GPT5_CODEX_INSTRUCTIONS")
        if (not isinstance(codex, str) or not codex.strip()) and hasattr(prompt_manager, "get_codex_instructions"):
            codex = prompt_manager.get_codex_instructions()
        if not isinstance(codex, str) or not codex.strip():
            codex = GPT5_CODEX_INSTRUCTIONS
        if isinstance(codex, str) and codex.strip():
            return codex
    return base


def fallback_passthrough_instructions() -> str:
    return (
        "Follow the developer and user instructions contained in the input. "
        "When calling tools, you must strictly match the provided tool schema. "
        "Do not call a tool with empty arguments unless the schema explicitly allows no arguments. "
        "Always include every required argument before making the tool call. "
        "If a tool call returns a schema error, inspect the schema and try again with corrected arguments."
    )


def resolve_effective_instructions(
    *,
    endpoint_kind: Literal["responses", "chat_completions", "completions"],
    payload: Dict[str, Any],
    model: str,
    config: Dict[str, Any],
) -> str:
    explicit = payload.get("instructions")
    if isinstance(explicit, str) and explicit.strip():
        return explicit
    if bool(config.get("INJECT_DEFAULT_INSTRUCTIONS", True)):
        return instructions_for_model(config, model)
    return fallback_passthrough_instructions()


def extract_client_session_id(headers: Any) -> str | None:
    try:
        return headers.get("X-Session-Id") or headers.get("session_id") or None
    except Exception:
        return None


def _input_items_for_session(raw_input: Any) -> List[Dict[str, Any]]:
    if isinstance(raw_input, list):
        return [item for item in raw_input if isinstance(item, dict)]
    if isinstance(raw_input, dict):
        return [raw_input]
    if isinstance(raw_input, str) and raw_input.strip():
        return [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": raw_input}],
            }
        ]
    return []


def canonicalize_responses_input(raw_input: Any) -> Any:
    if isinstance(raw_input, list):
        return [item for item in raw_input if isinstance(item, dict)]
    if isinstance(raw_input, dict):
        return [raw_input]
    if isinstance(raw_input, str):
        return _input_items_for_session(raw_input)
    return raw_input


def normalize_responses_payload(
    payload: Dict[str, Any],
    *,
    config: Dict[str, Any],
    client_session_id: str | None = None,
) -> NormalizedResponsesRequest:
    requested_model = payload.get("model") if isinstance(payload.get("model"), str) else None
    normalized_model = normalize_model_name(requested_model, config.get("DEBUG_MODEL"))

    normalized = dict(payload)
    normalized["model"] = normalized_model
    normalized.pop("max_output_tokens", None)
    normalized.pop("temperature", None)

    if "input" in normalized:
        normalized["input"] = canonicalize_responses_input(normalized.get("input"))

    if "store" not in normalized:
        normalized["store"] = False

    normalized["instructions"] = resolve_effective_instructions(
        endpoint_kind="responses",
        payload=normalized,
        model=normalized_model,
        config=config,
    )

    reasoning_effort = config.get("REASONING_EFFORT", "medium")
    reasoning_summary = config.get("REASONING_SUMMARY", "auto")
    reasoning_overrides = (
        normalized.get("reasoning")
        if isinstance(normalized.get("reasoning"), dict)
        else extract_reasoning_from_model_name(requested_model)
    )
    normalized["reasoning"] = build_reasoning_param(
        reasoning_effort,
        reasoning_summary,
        reasoning_overrides,
        allowed_efforts=allowed_efforts_for_model(normalized_model),
    )

    include = normalized.get("include")
    include_list = [item for item in include if isinstance(item, str)] if isinstance(include, list) else []
    if "reasoning.encrypted_content" not in include_list:
        include_list.append("reasoning.encrypted_content")
    normalized["include"] = include_list

    tools = normalized.get("tools")
    if (not isinstance(tools, list) or not tools) and bool(config.get("DEFAULT_WEB_SEARCH")):
        tool_choice = normalized.get("tool_choice")
        if not (isinstance(tool_choice, str) and tool_choice.strip().lower() == "none"):
            normalized["tools"] = [{"type": "web_search"}]

    service_tier_resolution = resolve_service_tier(
        normalized_model,
        request_fast_mode=normalized.get("fast_mode"),
        request_service_tier=normalized.get("service_tier"),
        server_fast_mode=bool(config.get("FAST_MODE")),
    )
    if service_tier_resolution.error_message:
        raise ResponsesRequestError(service_tier_resolution.error_message)
    if service_tier_resolution.service_tier is None:
        normalized.pop("service_tier", None)
    else:
        normalized["service_tier"] = service_tier_resolution.service_tier
    normalized.pop("fast_mode", None)

    input_items = _input_items_for_session(normalized.get("input"))
    session_id = ensure_session_id(normalized["instructions"], input_items, client_session_id)
    prompt_cache_key = normalized.get("prompt_cache_key")
    if not isinstance(prompt_cache_key, str) or not prompt_cache_key.strip():
        normalized["prompt_cache_key"] = session_id

    return NormalizedResponsesRequest(
        payload=normalized,
        requested_model=requested_model,
        normalized_model=normalized_model,
        session_id=session_id,
        service_tier_resolution=service_tier_resolution,
    )


@dataclass(frozen=True)
class SSEFrame:
    raw: bytes
    event: Dict[str, Any] | None


def _parse_sse_frame(raw_frame: bytes) -> Dict[str, Any] | None:
    text = raw_frame.replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("utf-8", errors="ignore")
    data_lines: List[str] = []
    event_type: str | None = None
    for line in text.splitlines():
        if line.startswith("event:"):
            payload = line[len("event:") :]
            if payload.startswith(" "):
                payload = payload[1:]
            if payload.strip():
                event_type = payload.strip()
            continue
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :]
        if payload.startswith(" "):
            payload = payload[1:]
        data_lines.append(payload)

    if not data_lines:
        return None

    data = "\n".join(data_lines).strip()
    if not data:
        return None
    if data == "[DONE]":
        return {"type": "[DONE]", "data": "[DONE]"}
    try:
        evt = json.loads(data)
    except json.JSONDecodeError:
        return None
    if not isinstance(evt, dict):
        return None
    if event_type and not isinstance(evt.get("type"), str):
        evt = evt.copy()
        evt["type"] = event_type
    return evt


def _split_sse_frame(buffer: bytes) -> tuple[bytes, bytes] | None:
    matches: List[tuple[int, bytes]] = []
    for delimiter in (b"\r\n\r\n", b"\n\r\n", b"\r\n\n", b"\n\n", b"\r\r"):
        idx = buffer.find(delimiter)
        if idx >= 0:
            matches.append((idx, delimiter))
    if not matches:
        return None
    idx, delimiter = min(matches, key=lambda item: item[0])
    end = idx + len(delimiter)
    return buffer[:end], buffer[end:]


def iter_sse_frames(upstream: Any) -> Iterator[SSEFrame]:
    buffer = b""
    for chunk in upstream.iter_content(chunk_size=None):
        if not chunk:
            continue
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        buffer += bytes(chunk)
        while True:
            split = _split_sse_frame(buffer)
            if split is None:
                break
            raw_frame, buffer = split
            yield SSEFrame(raw=raw_frame, event=_parse_sse_frame(raw_frame))

    if buffer:
        raw_frame = buffer if buffer.endswith(b"\n\n") else buffer + b"\n\n"
        yield SSEFrame(raw=raw_frame, event=_parse_sse_frame(raw_frame))


def iter_sse_event_payloads(upstream: Any) -> Iterator[Dict[str, Any]]:
    for frame in iter_sse_frames(upstream):
        if isinstance(frame.event, dict):
            yield frame.event
            if frame.event.get("data") == "[DONE]" or frame.event.get("type") == "[DONE]":
                break


def _tool_call_event_key(item_or_event: Dict[str, Any] | None) -> str | None:
    if not isinstance(item_or_event, dict):
        return None
    item_id = item_or_event.get("id")
    if isinstance(item_id, str) and item_id.strip():
        return item_id
    call_id = item_or_event.get("call_id")
    if isinstance(call_id, str) and call_id.strip():
        return call_id
    return None


def _is_buffered_tool_call_event(event: Dict[str, Any]) -> bool:
    item = event.get("item")
    if not isinstance(item, dict):
        return False
    return item.get("type") in ("function_call", "web_search_call", "web_search_preview_call")


def _output_text_event_key(event: Dict[str, Any]) -> tuple[Any, Any, Any] | None:
    item_id = event.get("item_id")
    output_index = event.get("output_index")
    content_index = event.get("content_index")
    if (
        (isinstance(item_id, str) and item_id.strip())
        or output_index is not None
        or content_index is not None
    ):
        return (item_id if isinstance(item_id, str) else None, output_index, content_index)
    return None


def _best_tool_arguments(
    pending: Dict[str, Any] | None,
    *,
    item: Dict[str, Any] | None = None,
    done_args: Any = None,
) -> Any:
    candidates: List[Any] = [done_args]
    if isinstance(item, dict):
        candidates.extend([item.get("arguments"), item.get("parameters")])
    if isinstance(pending, dict):
        candidates.append(pending.get("arguments_done"))
        added_event = pending.get("added_event")
        if isinstance(added_event, dict):
            added_item = added_event.get("item")
            if isinstance(added_item, dict):
                candidates.extend([added_item.get("arguments"), added_item.get("parameters")])
        buffer_parts = pending.get("argument_buffer_parts")
        if isinstance(buffer_parts, list):
            buffered = "".join(part for part in buffer_parts if isinstance(part, str) and part)
            if buffered:
                candidates.append(buffered)

    for raw in candidates:
        if isinstance(raw, str) and raw and raw.strip() not in ("{}", "[]", "null"):
            return raw
        if isinstance(raw, (dict, list)) and raw:
            return raw

    for raw in candidates:
        if isinstance(raw, str) and raw:
            return raw
        if isinstance(raw, (dict, list)):
            return raw
    return None


class ResponsesToolCallStreamNormalizer:
    def __init__(self) -> None:
        self._pending: Dict[str, Dict[str, Any]] = {}

    def flush(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for pending in self._pending.values():
            if pending.get("added_emitted"):
                continue
            added_event = copy.deepcopy(pending["added_event"])
            item = added_event.get("item")
            if isinstance(item, dict):
                best_args = _best_tool_arguments(pending, item=item)
                if best_args is not None:
                    item["arguments"] = best_args
            out.append(added_event)
        self._pending.clear()
        return out

    def _normalize_terminal_response_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        response = event.get("response")
        if not isinstance(response, dict):
            return event
        output = response.get("output")
        if not isinstance(output, list):
            return event

        normalized_event = event.copy()
        normalized_response = response.copy()
        normalized_output: List[Any] = []

        for raw_item in output:
            if not isinstance(raw_item, dict):
                normalized_output.append(raw_item)
                continue
            normalized_item = raw_item.copy()
            key = _tool_call_event_key(normalized_item)
            pending = self._pending.get(key) if isinstance(key, str) else None
            best_args = _best_tool_arguments(pending, item=normalized_item)
            if best_args is not None:
                normalized_item["arguments"] = best_args
            normalized_output.append(normalized_item)

        normalized_response["output"] = normalized_output
        normalized_event["response"] = normalized_response
        return normalized_event

    def process(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        kind = event.get("type")
        if kind == "response.output_item.added" and _is_buffered_tool_call_event(event):
            item = event.get("item")
            key = _tool_call_event_key(item)
            if key:
                self._pending[key] = {
                    "added_event": copy.deepcopy(event),
                    "added_emitted": False,
                    "argument_buffer_parts": [],
                    "arguments_done": None,
                }
                return []

        if kind == "response.function_call_arguments.delta":
            key = event.get("item_id")
            pending = self._pending.get(key) if isinstance(key, str) else None
            if pending is not None:
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    buffer_parts = pending.setdefault("argument_buffer_parts", [])
                    if isinstance(buffer_parts, list):
                        buffer_parts.append(delta)
                return []

        if kind == "response.function_call_arguments.done":
            key = event.get("item_id")
            pending = self._pending.get(key) if isinstance(key, str) else None
            if pending is not None:
                pending["arguments_done"] = event.get("arguments")
                out: List[Dict[str, Any]] = []
                best_args = _best_tool_arguments(
                    pending,
                    done_args=event.get("arguments"),
                )
                if not pending["added_emitted"]:
                    added_event = copy.deepcopy(pending["added_event"])
                    item = added_event.get("item")
                    if isinstance(item, dict):
                        if best_args is not None:
                            item["arguments"] = best_args
                    pending["added_emitted"] = True
                    out.append(added_event)
                done_event = event.copy()
                if best_args is not None:
                    done_event["arguments"] = best_args
                out.append(done_event)
                return out

        if kind == "response.output_item.done" and _is_buffered_tool_call_event(event):
            item = event.get("item")
            key = _tool_call_event_key(item)
            pending = self._pending.get(key) if isinstance(key, str) else None
            if pending is not None:
                out = []
                best_args = _best_tool_arguments(
                    pending,
                    item=item if isinstance(item, dict) else None,
                    done_args=pending.get("arguments_done"),
                )
                if not pending["added_emitted"]:
                    added_event = copy.deepcopy(pending["added_event"])
                    added_item = added_event.get("item")
                    if isinstance(added_item, dict):
                        if best_args is not None:
                            added_item["arguments"] = best_args
                    pending["added_emitted"] = True
                    out.append(added_event)
                done_event = event.copy()
                done_item = done_event.get("item")
                if isinstance(done_item, dict):
                    done_item = done_item.copy()
                    done_event["item"] = done_item
                if isinstance(done_item, dict) and best_args is not None:
                    done_item["arguments"] = best_args
                out.append(done_event)
                return out

        if kind in ("response.completed", "response.failed", "error") and self._pending:
            out: List[Dict[str, Any]] = []
            for pending in self._pending.values():
                if pending.get("added_emitted"):
                    continue
                added_event = copy.deepcopy(pending["added_event"])
                item = added_event.get("item")
                if isinstance(item, dict):
                    best_args = _best_tool_arguments(pending, item=item)
                    if best_args is not None:
                        item["arguments"] = best_args
                out.append(added_event)
            event = self._normalize_terminal_response_event(event)
            self._pending.clear()
            out.append(event)
            return out

        return [event]


def iter_normalized_response_events(events: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    normalizer = ResponsesToolCallStreamNormalizer()
    for event in events:
        if event.get("data") == "[DONE]" or event.get("type") == "[DONE]":
            for normalized in normalizer.flush():
                yield normalized
            yield event
            return
        for normalized in normalizer.process(event):
            yield normalized
    for normalized in normalizer.flush():
        yield normalized


def aggregate_response_from_sse(
    upstream: Any,
    *,
    on_event: Any | None = None,
) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    response_obj: Dict[str, Any] | None = None
    error_obj: Dict[str, Any] | None = None
    output_items: List[Dict[str, Any]] = []
    output_text_parts: List[str] = []
    output_text_delta_keys: set[tuple[Any, Any, Any]] = set()
    completed_event: Dict[str, Any] | None = None
    try:
        for evt in iter_normalized_response_events(iter_sse_event_payloads(upstream)):
            response = evt.get("response")
            if isinstance(response, dict):
                response_obj = response
            kind = evt.get("type")
            if kind == "response.completed":
                completed_event = evt
                break
            if callable(on_event):
                try:
                    on_event(evt)
                except Exception:
                    pass
            if kind == "response.output_text.delta":
                delta = evt.get("delta")
                if isinstance(delta, str) and delta:
                    key = _output_text_event_key(evt)
                    if key is not None:
                        output_text_delta_keys.add(key)
                    output_text_parts.append(delta)
            elif kind == "response.output_text.done":
                text = evt.get("text")
                if isinstance(text, str) and text:
                    key = _output_text_event_key(evt)
                    if key is None:
                        if not "".join(output_text_parts).endswith(text):
                            output_text_parts.append(text)
                    elif key not in output_text_delta_keys:
                        output_text_parts.append(text)
            elif kind == "response.output_item.done":
                item = evt.get("item")
                if isinstance(item, dict):
                    output_items.append(item)
            if kind == "response.failed":
                if isinstance(response, dict) and isinstance(response.get("error"), dict):
                    error_obj = {"error": response.get("error")}
                else:
                    error_obj = {"error": {"message": "response.failed"}}
                break
    finally:
        upstream.close()
    if response_obj is not None:
        response_obj = _populate_response_output_from_stream(
            response_obj,
            output_items=output_items,
            output_text="".join(output_text_parts),
        )
    if completed_event is not None and callable(on_event):
        enriched_event = completed_event.copy()
        if response_obj is not None:
            enriched_event["response"] = response_obj
        try:
            on_event(enriched_event)
        except Exception:
            pass
    return response_obj, error_obj


def _populate_response_output_from_stream(
    response_obj: Dict[str, Any],
    *,
    output_items: List[Dict[str, Any]],
    output_text: str,
) -> Dict[str, Any]:
    populated = response_obj.copy()
    existing_output = populated.get("output")
    has_output = isinstance(existing_output, list) and bool(existing_output)

    if not has_output:
        if output_items:
            populated["output"] = output_items
            has_output = True
        elif output_text:
            parent_id = populated.get("id")
            synthesized_id = f"msg_{parent_id}" if isinstance(parent_id, str) and parent_id else None
            populated["output"] = [
                {
                    **({"id": synthesized_id} if synthesized_id else {}),
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": output_text}],
                }
            ]
            has_output = True

    if output_text and not populated.get("output_text"):
        populated["output_text"] = output_text
    elif has_output and not populated.get("output_text"):
        text_from_items = _response_output_text(populated.get("output"))
        if text_from_items:
            populated["output_text"] = text_from_items

    return populated


def _response_output_text(output: Any) -> str:
    if not isinstance(output, list):
        return ""
    parts: List[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
    return "".join(parts)


def stream_upstream_bytes(
    upstream: Any,
    *,
    on_event: Any | None = None,
) -> Iterable[bytes]:
    try:
        normalizer = ResponsesToolCallStreamNormalizer()
        for frame in iter_sse_frames(upstream):
            evt = frame.event
            if not isinstance(evt, dict):
                yield frame.raw
                continue

            for normalized in normalizer.process(evt):
                if callable(on_event):
                    try:
                        on_event(normalized)
                    except Exception:
                        pass
                event_type = normalized.get("type")
                if normalized.get("data") == "[DONE]" or event_type == "[DONE]":
                    for flushed in normalizer.flush():
                        if callable(on_event):
                            try:
                                on_event(flushed)
                            except Exception:
                                pass
                        payload = json.dumps(flushed, ensure_ascii=False)
                        yield f"data: {payload}\n\n".encode("utf-8")
                    yield frame.raw
                    return
                payload = json.dumps(normalized, ensure_ascii=False)
                yield f"data: {payload}\n\n".encode("utf-8")
        for normalized in normalizer.flush():
            if callable(on_event):
                try:
                    on_event(normalized)
                except Exception:
                    pass
            payload = json.dumps(normalized, ensure_ascii=False)
            yield f"data: {payload}\n\n".encode("utf-8")
    finally:
        upstream.close()
