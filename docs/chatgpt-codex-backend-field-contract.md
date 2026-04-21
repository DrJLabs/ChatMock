# ChatGPT Codex backend field contract

This document captures the **empirically observed** request contract for the private backend that ChatMock targets:

- `https://chatgpt.com/backend-api/codex/responses`

It is **not** a copy of the public OpenAI `v1/responses` schema. The public API accepts more fields than this private backend.

## Status and scope

- Probe date: 2026-04-17
- Probe lane: authenticated direct requests using ChatMock's local auth/session path
- Request mode: SSE only (`stream=true`)
- Baseline model used for probes: `gpt-5.4-mini`

Treat this as a compatibility reference for ChatMock's upstream adapter, not as an official OpenAI API spec.

## Required request fields

These request fields are required for successful requests:

- `model`
- `instructions`
- `input`
- `stream`
- `store`

## Required value constraints

These fields also have backend-specific value requirements:

- `stream` must be `true`
- `store` must be `false`
- `input` must be a **list**
- `instructions` must be present
- `model` must be supported by the Codex backend for ChatGPT accounts

## Confirmed accepted request fields

The following top-level request fields were explicitly accepted in live probes.

### Core

- `model`
- `instructions`
- `input`
- `stream`
- `store`

### Tooling

- `tools`
- `tool_choice`
- `parallel_tool_calls`

### Session / cache

- `prompt_cache_key`

### Reasoning / output shaping

- `include`
  - confirmed example: `["reasoning.encrypted_content"]`
- `reasoning`
  - confirmed example: `{ "effort": "low" }`
- `text`
  - confirmed examples:
    - `{ "format": { "type": "text" } }`
    - `{ "format": { "type": "text" }, "verbosity": "low" }`

### Service tier

- `service_tier`
  - confirmed accepted request value: `priority`
  - observed response normalization: accepted `priority` requests were echoed back as `service_tier: "auto"` in `response.created`

## Confirmed rejected request fields

The following top-level request fields returned `400` when explicitly sent:

- `background`
- `max_output_tokens`
- `max_tool_calls`
- `metadata`
- `prompt_cache_retention`
- `safety_identifier`
- `stream_options`
- `temperature`
- `top_logprobs`
- `top_p`
- `truncation`
- `user`
- `presence_penalty`
- `frequency_penalty`
- `previous_response_id`
- `conversation`
- `prompt`

## Confirmed rejected values / shapes

The backend also rejects these invalid-but-tempting shapes or values:

- `stream: false`
  - response: `Stream must be set to true`
- `store: true`
  - response: `Store must be set to false`
- `input: "string"`
  - response: `Input must be a list`
- missing `input`
  - response: missing required parameter error
- missing `instructions`
  - response: `Instructions are required`
- `service_tier: auto`
  - response: unsupported service tier
- `service_tier: default`
  - response: unsupported service tier

## Important caveat: response fields are not request fields

The backend's `response.created` payload includes fields such as:

- `temperature`
- `top_p`
- `truncation`
- `metadata`
- `prompt_cache_retention`
- `presence_penalty`
- `frequency_penalty`
- `safety_identifier`

However, their presence in the response does **not** mean they are safe request parameters. In live probes, several of these fields were echoed in responses while still being rejected as explicit request inputs.

## Safe operational allowlist for ChatMock

For ChatMock's upstream adapter, the following request allowlist is currently safe:

- `model`
- `instructions`
- `input`
- `tools`
- `tool_choice`
- `parallel_tool_calls`
- `store=false`
- `stream=true`
- `prompt_cache_key`
- `include`
- `reasoning`
- `text`
- optionally `service_tier`, but only with validated values

## Safe operational denylist for ChatMock

These fields should be stripped or withheld when targeting the ChatGPT Codex backend:

- `background`
- `max_output_tokens`
- `max_tool_calls`
- `metadata`
- `prompt_cache_retention`
- `safety_identifier`
- `stream_options`
- `temperature`
- `top_logprobs`
- `top_p`
- `truncation`
- `user`
- `presence_penalty`
- `frequency_penalty`
- `previous_response_id`
- `conversation`
- `prompt`

## Re-probe guidance

If this backend behavior becomes relevant again, re-run a live probe instead of assuming public Responses API parity.

Suggested probe characteristics:

- use ChatMock's actual auth/session path
- send SSE requests with `stream=true`
- compare a known-good baseline request against a single added candidate field
- classify each candidate as:
  - accepted
  - rejected with explicit error
  - inconclusive / needs deeper probing

This backend is private and may change independently of public OpenAI API documentation.
