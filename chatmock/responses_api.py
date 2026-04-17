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
    base = config.get("BASE_INSTRUCTIONS", BASE_INSTRUCTIONS)
    if uses_codex_instructions(model):
        codex = config.get("GPT5_CODEX_INSTRUCTIONS") or GPT5_CODEX_INSTRUCTIONS
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
    explicit = payload.get("instructions") if endpoint_kind == "responses" else None
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


def iter_sse_event_payloads(upstream: Any) -> Iterator[Dict[str, Any]]:
    for raw in upstream.iter_lines(decode_unicode=False):
        if not raw:
            continue
        line = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else raw
        if not line.startswith("data: "):
            continue
        data = line[len("data: ") :].strip()
        if not data or data == "[DONE]":
            if data == "[DONE]":
                break
            continue
        try:
            evt = json.loads(data)
        except Exception:
            continue
        if isinstance(evt, dict):
            yield evt


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
    return item.get("type") in ("function_call", "web_search_call")


def _best_tool_arguments(
    pending: Dict[str, Any] | None,
    *,
    item: Dict[str, Any] | None = None,
    done_args: Any = None,
) -> Any:
    if isinstance(done_args, str) and done_args:
        return done_args
    if isinstance(done_args, (dict, list)):
        return done_args
    if isinstance(item, dict):
        raw = item.get("arguments")
        if isinstance(raw, str) and raw:
            return raw
        if isinstance(raw, (dict, list)):
            return raw
        raw = item.get("parameters")
        if isinstance(raw, str) and raw:
            return raw
        if isinstance(raw, (dict, list)):
            return raw
    if isinstance(pending, dict):
        raw = pending.get("arguments_done")
        if isinstance(raw, str) and raw:
            return raw
        if isinstance(raw, (dict, list)):
            return raw
        raw = pending.get("argument_buffer")
        if isinstance(raw, str) and raw:
            return raw
    return None


class ResponsesToolCallStreamNormalizer:
    def __init__(self) -> None:
        self._pending: Dict[str, Dict[str, Any]] = {}

    def process(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        kind = event.get("type")
        if kind == "response.output_item.added" and _is_buffered_tool_call_event(event):
            item = event.get("item")
            key = _tool_call_event_key(item)
            if key:
                self._pending[key] = {
                    "added_event": copy.deepcopy(event),
                    "added_emitted": False,
                    "argument_buffer": "",
                    "arguments_done": None,
                }
                return []

        if kind == "response.function_call_arguments.delta":
            key = event.get("item_id")
            pending = self._pending.get(key) if isinstance(key, str) else None
            if pending is not None:
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    pending["argument_buffer"] = f"{pending['argument_buffer']}{delta}"
                return []

        if kind == "response.function_call_arguments.done":
            key = event.get("item_id")
            pending = self._pending.get(key) if isinstance(key, str) else None
            if pending is not None:
                pending["arguments_done"] = event.get("arguments")
                out: List[Dict[str, Any]] = []
                if not pending["added_emitted"]:
                    added_event = copy.deepcopy(pending["added_event"])
                    item = added_event.get("item")
                    if isinstance(item, dict):
                        best_args = _best_tool_arguments(pending, item=item, done_args=event.get("arguments"))
                        if best_args is not None:
                            item["arguments"] = best_args
                    pending["added_emitted"] = True
                    out.append(added_event)
                out.append(event)
                return out

        if kind == "response.output_item.done" and _is_buffered_tool_call_event(event):
            item = event.get("item")
            key = _tool_call_event_key(item)
            pending = self._pending.pop(key, None) if isinstance(key, str) else None
            if pending is not None:
                out = []
                if not pending["added_emitted"]:
                    added_event = copy.deepcopy(pending["added_event"])
                    added_item = added_event.get("item")
                    if isinstance(added_item, dict):
                        best_args = _best_tool_arguments(pending, item=item if isinstance(item, dict) else None)
                        if best_args is not None:
                            added_item["arguments"] = best_args
                    out.append(added_event)
                out.append(event)
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
            self._pending.clear()
            out.append(event)
            return out

        return [event]


def iter_normalized_response_events(events: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    normalizer = ResponsesToolCallStreamNormalizer()
    for event in events:
        for normalized in normalizer.process(event):
            yield normalized


def aggregate_response_from_sse(
    upstream: Any,
    *,
    on_event: Any | None = None,
) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    response_obj: Dict[str, Any] | None = None
    error_obj: Dict[str, Any] | None = None
    try:
        for evt in iter_normalized_response_events(iter_sse_event_payloads(upstream)):
            if callable(on_event):
                try:
                    on_event(evt)
                except Exception:
                    pass
            response = evt.get("response")
            if isinstance(response, dict):
                response_obj = response
            kind = evt.get("type")
            if kind == "response.failed":
                if isinstance(response, dict) and isinstance(response.get("error"), dict):
                    error_obj = {"error": response.get("error")}
                else:
                    error_obj = {"error": {"message": "response.failed"}}
                break
            if kind == "response.completed":
                break
    finally:
        upstream.close()
    return response_obj, error_obj


def stream_upstream_bytes(
    upstream: Any,
    *,
    on_event: Any | None = None,
) -> Iterable[bytes]:
    try:
        for evt in iter_normalized_response_events(iter_sse_event_payloads(upstream)):
            if callable(on_event):
                try:
                    on_event(evt)
                except Exception:
                    pass
            event_type = evt.get("type")
            payload = json.dumps(evt, ensure_ascii=False)
            if isinstance(event_type, str) and event_type.strip():
                yield f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")
            else:
                yield f"data: {payload}\n\n".encode("utf-8")
    finally:
        upstream.close()
