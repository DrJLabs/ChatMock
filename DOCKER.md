# Docker Deployment

## Quick Start
1) Setup env:
   cp .env.example .env

2) Login:
   docker compose run --rm --service-ports chatmock-login login

   - The command prints an auth URL, copy paste it into your browser.
   - If your browser cannot reach the container's localhost callback, copy the full redirect URL from the browser address bar and paste it back into the terminal when prompted.
   - Server should stop automatically once it receives the tokens and they are saved.

3) Start the server:
   docker compose up -d chatmock

4) Free to use it in whichever chat app you like!

## Live prompt switching

The compose stack now mounts the whole `./prompts` tree into `/app/prompts` and each service keeps its own runtime prompt config file under `/data`.

Default runtime prompt selection:

- `chatmock` uses `${CHATMOCK_PROMPT_DIR:-/app/prompts/bare}`
- `chatmock-clawmem` uses `${CHATMOCK_CLAWMEM_PROMPT_DIR:-/app/prompts/clawmem}`

Live prompt controls are local-only:

- `GET /admin/prompts`
- `POST /admin/prompts/reload`
- `POST /admin/prompts/config`

Example: switch the main service to the ClawMem prompt directory without restarting the container:

```bash
curl -sS -X POST http://127.0.0.1:8000/admin/prompts/config \
  -H 'Content-Type: application/json' \
  -d '{"prompt_dir":"/app/prompts/clawmem"}' | jq .
```

Example: reload prompt file contents after editing files in the mounted directory:

```bash
curl -sS -X POST http://127.0.0.1:8000/admin/prompts/reload | jq .
```

## Isolated test stack

Use the override file to bring up a disposable stack on separate ports without touching the live services or their `/data` volume.

Bring it up:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml -p chatmock-test up -d chatmock chatmock-clawmem
```

Verify it:

```bash
curl -fsS http://127.0.0.1:18000/health
curl -fsS http://127.0.0.1:18001/health
```

Tear it down completely:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml -p chatmock-test down -v
```

The override isolates:

- ports: `18000`, `18001`, `11455`
- container names: `chatmock-test`, `chatmock-clawmem-test`
- prompt runtime config files under the test stack's own `/data`
- writable runtime state in the test stack's own `chatmock-test_chatmock_data` volume

The override also mounts the live stack's auth volume read-only at `/live-auth` and sets `CODEX_HOME=/live-auth`, so the test services can reuse existing auth without sharing the live stack's writable runtime state.

## Configuration
Set options in `.env` or pass environment variables:
- `PORT`: Container listening port (default 8000)
- `CHATMOCK_IMAGE`: image tag to run (default `storagetime/chatmock:latest`)
- `VERBOSE`: `true|false` to enable request/stream logs
- `CHATGPT_LOCAL_REASONING_EFFORT`: minimal|low|medium|high|xhigh
- `CHATGPT_LOCAL_REASONING_SUMMARY`: auto|concise|detailed|none
- `CHATGPT_LOCAL_REASONING_COMPAT`: legacy|o3|think-tags|current
- `CHATGPT_LOCAL_FAST_MODE`: `true|false` to enable fast mode by default for supported models
- `CHATGPT_LOCAL_CLIENT_ID`: OAuth client id override (rarely needed)
- `CHATGPT_LOCAL_EXPOSE_REASONING_MODELS`: `true|false` to add reasoning model variants to `/v1/models`
- `CHATGPT_LOCAL_ENABLE_WEB_SEARCH`: `true|false` to enable default web search tool
- `CHATMOCK_PROMPT_DIR`: default prompt directory for the main service
- `CHATMOCK_PROMPT_CONFIG`: runtime prompt config file for the main service
- `CHATMOCK_CLAWMEM_PROMPT_DIR`: default prompt directory for the ClawMem service
- `CHATMOCK_CLAWMEM_PROMPT_CONFIG`: runtime prompt config file for the ClawMem service
- `CHATMOCK_ADMIN_TOKEN`: optional token required by the `/admin/prompts/*` endpoints when set
- `CHATMOCK_TEST_PORT`: main service port for the isolated test stack
- `CHATMOCK_TEST_CLAWMEM_PORT`: ClawMem service port for the isolated test stack
- `CHATMOCK_TEST_LOGIN_PORT`: login callback port for the isolated test stack
- `CHATMOCK_TEST_PROMPT_DIR`: main service prompt dir in the isolated test stack
- `CHATMOCK_TEST_PROMPT_CONFIG`: main service runtime prompt config in the isolated test stack
- `CHATMOCK_TEST_CLAWMEM_PROMPT_DIR`: ClawMem prompt dir in the isolated test stack
- `CHATMOCK_TEST_CLAWMEM_PROMPT_CONFIG`: ClawMem runtime prompt config in the isolated test stack

## Logs
Set `VERBOSE=true` to include extra logging for troubleshooting upstream or chat app requests. Please include and use these logs when submitting bug reports.

## Test

```
curl -s http://localhost:8000/v1/chat/completions \
   -H 'Content-Type: application/json' \
   -d '{"model":"gpt-5-codex","messages":[{"role":"user","content":"Hello world!"}]}' | jq .
```
