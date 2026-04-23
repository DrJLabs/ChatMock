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

Registry-backed management metadata now also lives in:

- `config/profiles/*.yaml`
- `config/instances/*.yaml`

Those registry files are used for validation, instance listing, and runtime previews.
They do not replace the live prompt manager or the live `docker-compose.yml` entrypoint in this phase.

Default runtime prompt selection:

- `chatmock` uses `${CHATMOCK_PROMPT_DIR:-/app/prompts/bare}`
- `chatmock-clawmem` uses `${CHATMOCK_CLAWMEM_PROMPT_DIR:-/app/prompts/clawmem}`

Live prompt controls are local-only:

- `GET /admin/prompts`
- `POST /admin/prompts/reload`
- `POST /admin/prompts/config`

If `CHATMOCK_ADMIN_TOKEN` is configured, include the header:

```bash
-H "X-ChatMock-Admin-Token: $CHATMOCK_ADMIN_TOKEN"
```

By default the admin endpoints only accept:

- loopback clients
- known Docker host gateway addresses such as `172.17.0.1` and `172.18.0.1`

If your Docker/network setup uses a different host address, set:

```bash
CHATMOCK_ALLOW_ADMIN_EXTERNAL=true
```

and rely on `CHATMOCK_ADMIN_TOKEN` for access control. External admin access is rejected unless a non-empty `CHATMOCK_ADMIN_TOKEN` is configured.

For non-standard container networks, you can also trust specific admin IPs or CIDR ranges:

```bash
CHATMOCK_ADMIN_TRUSTED_IPS=172.17.0.1,10.0.0.0/8
```

Example: switch the main service to the ClawMem prompt directory without restarting the container:

```bash
curl -sS -X POST http://127.0.0.1:8000/admin/prompts/config \
  -H "X-ChatMock-Admin-Token: $CHATMOCK_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"prompt_dir":"/app/prompts/clawmem"}' | jq .
```

Example: reload prompt file contents after editing files in the mounted directory:

```bash
curl -sS -X POST http://127.0.0.1:8000/admin/prompts/reload \
  -H "X-ChatMock-Admin-Token: $CHATMOCK_ADMIN_TOKEN" | jq .
```

## Instance registry inspection

Registry-backed management now exposes both current-state and draft/apply controls locally:

- `GET /admin/profiles`
- `GET /admin/instances`
- `GET /admin/instances/<instance_id>/preview`
- `GET /admin/draft`
- `POST /admin/draft/reset`
- `POST /admin/draft/validate`
- `POST /admin/draft/preview`
- `POST /admin/draft/apply`
- `POST /admin/profiles`
- `PUT /admin/profiles/<profile_id>`
- `DELETE /admin/profiles/<profile_id>`
- `POST /admin/instances`
- `PUT /admin/instances/<instance_id>`
- `DELETE /admin/instances/<instance_id>`
- `POST /admin/runtime/validate`
- `POST /admin/runtime/prompts/reload`
- `POST /admin/runtime/redeploy`

CLI equivalents:

```bash
chatmock instances list
chatmock instances validate
chatmock instances preview chatmock
```

These controls now back the in-repo browser admin UI and keep the split between:

- immediate runtime actions
- draft/apply structural edits

## Browser Admin UI

The primary operator UI now lives in-repo under:

- `ui/admin/`

Default local test port for both backend and browser-admin changes:

- `18000`

Use that as the default verification target when you want an isolated test server without touching the live service on `8000`.

Development loop:

```bash
chatmock serve --port 18000

cd ui/admin
npm install
npm run dev
```

The Vite dev server currently proxies `/admin/*` requests to the Flask backend on `http://127.0.0.1:8000`, so for branch testing the simpler default is to use the Flask-served built UI on `18000`:

```bash
cd ui/admin
npm run build

curl -I http://127.0.0.1:18000/admin/ui
curl -fsS http://127.0.0.1:18000/admin/draft | jq .
```

Production build:

```bash
cd ui/admin
npm run build
```

That emits static assets to:

- `ui/admin/dist/`

The container image also builds and ships these assets during `docker build`.
At runtime the Flask app uses:

- `CHATMOCK_ADMIN_UI_DIST_DIR=/app/ui/admin/dist`

unless an explicit `admin_ui_dist_dir` or env override is provided.

The runtime image now switches to the non-root `chatmock` user. Named Docker volumes preserve the in-image `/data` ownership, but a host bind mount will override it with the host directory's UID/GID. If you bind-mount `/data`, make sure the host path is writable by the container user, use a Compose `user:` override, or fix host ownership first:

```bash
sudo chown -R <container-uid>:<container-gid> /path/to/your/chatmock-data
```

Flask serves the built SPA at:

- `GET /admin/ui`
- `GET /admin/ui/<path>`

The SPA inherits the same local-only trust model as the JSON admin endpoints. That means tailnet exposure should happen through the existing local hosting model plus Tailscale Serve or an equivalent tailnet-only path, not through a second login/session layer.

The browser UI is intentionally single-user. Structural edits happen in one in-memory draft owned by the Flask process:

- profile and instance edits change only the draft
- `POST /admin/draft/validate` checks the draft without writing YAML
- `POST /admin/draft/preview` renders instance/runtime previews from the draft
- `POST /admin/draft/apply` writes the YAML-backed config and refreshes the live current-state snapshot
- runtime actions such as prompt reload and redeploy stay separate from Apply

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

If your live stack uses a different Compose project name, set the external auth volume explicitly:

```bash
CHATMOCK_TEST_AUTH_VOLUME=<your_live_project>_chatmock_data
```

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
- `CHATMOCK_ADMIN_TRUSTED_IPS`: optional comma-separated trusted admin IPs/CIDRs for non-standard local container networks
- `CHATMOCK_ALLOW_ADMIN_EXTERNAL`: allow non-local admin access only when paired with `CHATMOCK_ADMIN_TOKEN`
- `CHATMOCK_TEST_PORT`: main service port for the isolated test stack
- `CHATMOCK_TEST_CLAWMEM_PORT`: ClawMem service port for the isolated test stack
- `CHATMOCK_TEST_LOGIN_PORT`: login callback port for the isolated test stack
- `CHATMOCK_TEST_AUTH_VOLUME`: external live auth volume name mounted read-only into the isolated test stack
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
