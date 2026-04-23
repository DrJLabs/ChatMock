from __future__ import annotations

import hmac
import ipaddress
import os
from pathlib import Path

from flask import Flask, jsonify, request
from flask_sock import Sock

from .admin_draft_service import AdminDraftService
from .admin_routes import admin_bp
from .config import get_prompt_manager
from .http import build_cors_headers
from .instance_service import build_instance_service
from .routes_openai import openai_bp
from .routes_ollama import ollama_bp
from .websocket_routes import register_websocket_routes


def _discover_default_gateway_ips() -> set[str]:
    route_path = Path("/proc/net/route")
    try:
        lines = route_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()

    gateways: set[str] = set()
    for line in lines[1:]:
        fields = line.split()
        if len(fields) < 4:
            continue
        destination, gateway, flags = fields[1], fields[2], fields[3]
        try:
            if destination != "00000000" or not (int(flags, 16) & 0x2):
                continue
            gateway_bytes = bytes.fromhex(gateway)
            if len(gateway_bytes) != 4:
                continue
            gateway_ip = ipaddress.IPv4Address(int.from_bytes(gateway_bytes, "little"))
        except ValueError:
            continue
        gateways.add(str(gateway_ip))
    return gateways


def create_app(
    verbose: bool = False,
    verbose_obfuscation: bool = False,
    reasoning_effort: str = "medium",
    reasoning_summary: str = "auto",
    reasoning_compat: str = "think-tags",
    fast_mode: bool = False,
    debug_model: str | None = None,
    expose_reasoning_models: bool = False,
    default_web_search: bool = False,
    inject_default_instructions: bool = True,
    prompt_dir: str | None = None,
    prompt_config_path: str | None = None,
    admin_token: str | None = None,
    admin_ui_dist_dir: str | None = None,
    repo_root: str | None = None,
    profiles_root: str | None = None,
    instances_root: str | None = None,
    runtime_redeploy_callback=None,
) -> Flask:
    app = Flask(__name__)
    repo_root_path = Path(repo_root) if isinstance(repo_root, str) and repo_root else None
    allowed_gateway_addresses = _discover_default_gateway_ips()
    prompt_manager = get_prompt_manager(
        prompt_dir=prompt_dir,
        prompt_config_path=prompt_config_path,
        reset=True,
    )

    app.config.update(
        VERBOSE=bool(verbose),
        VERBOSE_OBFUSCATION=bool(verbose_obfuscation),
        REASONING_EFFORT=reasoning_effort,
        REASONING_SUMMARY=reasoning_summary,
        REASONING_COMPAT=reasoning_compat,
        FAST_MODE=bool(fast_mode),
        DEBUG_MODEL=debug_model,
        EXPOSE_REASONING_MODELS=bool(expose_reasoning_models),
        DEFAULT_WEB_SEARCH=bool(default_web_search),
        INJECT_DEFAULT_INSTRUCTIONS=bool(inject_default_instructions),
        PROMPT_MANAGER=prompt_manager,
        INSTANCE_SERVICE=None,
        DRAFT_SERVICE=None,
        ADMIN_UI_DIST_DIR=(
            admin_ui_dist_dir
            if isinstance(admin_ui_dist_dir, str) and admin_ui_dist_dir.strip()
            else os.getenv("CHATMOCK_ADMIN_UI_DIST_DIR") or None
        ),
        ALLOWED_GATEWAY_ADDRESSES=allowed_gateway_addresses,
        REPO_ROOT=repo_root_path,
        PROFILES_ROOT=profiles_root,
        INSTANCES_ROOT=instances_root,
        RUNTIME_REDEPLOY_CALLBACK=runtime_redeploy_callback,
        ADMIN_TOKEN=(
            admin_token
            if isinstance(admin_token, str) and admin_token
            else os.getenv("CHATMOCK_ADMIN_TOKEN") or os.getenv("CHATGPT_LOCAL_ADMIN_TOKEN") or None
        ),
    )

    @app.get("/")
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    def _require_local_admin():
        remote_addr = request.remote_addr
        allow_admin_external = os.getenv("CHATMOCK_ALLOW_ADMIN_EXTERNAL", "false").lower() == "true"
        allowed_local_addresses = {"127.0.0.1", "::1"}
        allowed_gateway_addresses = app.config.get("ALLOWED_GATEWAY_ADDRESSES") or set()
        trusted_remote_spec = os.getenv("CHATMOCK_ADMIN_TRUSTED_IPS", "").strip()

        def _is_in_trusted_ranges(value: str | None) -> bool:
            if not isinstance(value, str) or not value or not trusted_remote_spec:
                return False
            try:
                remote_ip = ipaddress.ip_address(value)
            except ValueError:
                return False
            for token in (item.strip() for item in trusted_remote_spec.split(",")):
                if not token:
                    continue
                try:
                    if "/" in token:
                        if remote_ip in ipaddress.ip_network(token, strict=False):
                            return True
                    elif remote_ip == ipaddress.ip_address(token):
                        return True
                except ValueError:
                    continue
            return False

        is_allowed_gateway = isinstance(remote_addr, str) and remote_addr in allowed_gateway_addresses
        is_local = isinstance(remote_addr, str) and remote_addr in allowed_local_addresses
        is_trusted_remote = _is_in_trusted_ranges(remote_addr)
        if not (is_local or is_allowed_gateway or is_trusted_remote or allow_admin_external):
            return jsonify({"error": {"message": "Admin routes are local-only"}}), 403
        expected_token = app.config.get("ADMIN_TOKEN")
        provided_token = (
            request.headers.get("X-ChatMock-Admin-Token")
            or request.headers.get("X-Admin-Token")
            or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        )
        if allow_admin_external and not (is_local or is_allowed_gateway or is_trusted_remote):
            if not (isinstance(expected_token, str) and expected_token):
                return jsonify({"error": {"message": "External admin access requires CHATMOCK_ADMIN_TOKEN"}}), 403
        if isinstance(expected_token, str) and expected_token:
            if not isinstance(provided_token, str) or not hmac.compare_digest(provided_token, expected_token):
                return jsonify({"error": {"message": "Invalid admin token"}}), 403
        return None

    def _get_instance_service():
        service = app.config.get("INSTANCE_SERVICE")
        if service is None:
            service = build_instance_service(
                repo_root=repo_root_path,
                profiles_root=profiles_root,
                instances_root=instances_root,
            )
            app.config["INSTANCE_SERVICE"] = service
        return service

    def _get_draft_service():
        service = app.config.get("DRAFT_SERVICE")
        if service is None:
            service = AdminDraftService(
                repo_root=repo_root_path or Path(__file__).resolve().parent.parent,
                profiles_root=profiles_root,
                instances_root=instances_root,
            )
            app.config["DRAFT_SERVICE"] = service
        return service

    def _registry_error(exc: Exception):
        return jsonify({"error": {"message": str(exc)}}), 400

    app.config.update(
        REQUIRE_LOCAL_ADMIN=_require_local_admin,
        GET_INSTANCE_SERVICE=_get_instance_service,
        GET_DRAFT_SERVICE=_get_draft_service,
        REGISTRY_ERROR_HANDLER=_registry_error,
    )

    @app.after_request
    def _cors(resp):
        for k, v in build_cors_headers().items():
            resp.headers.setdefault(k, v)
        return resp

    app.register_blueprint(admin_bp)
    app.register_blueprint(openai_bp)
    app.register_blueprint(ollama_bp)
    sock = Sock(app)
    register_websocket_routes(sock)

    return app
