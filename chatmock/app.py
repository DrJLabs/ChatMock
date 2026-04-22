from __future__ import annotations

import os

from flask import Flask, jsonify, request
from flask_sock import Sock
from werkzeug.exceptions import BadRequest

from .config import get_prompt_manager
from .http import build_cors_headers
from .routes_openai import openai_bp
from .routes_ollama import ollama_bp
from .websocket_routes import register_websocket_routes


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
) -> Flask:
    app = Flask(__name__)
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
        allowed_bridge_addresses = {"172.17.0.1", "172.18.0.1"}
        is_allowed_bridge = isinstance(remote_addr, str) and remote_addr in allowed_bridge_addresses
        is_local = isinstance(remote_addr, str) and remote_addr in allowed_local_addresses
        if not (is_local or is_allowed_bridge or allow_admin_external):
            return jsonify({"error": {"message": "Admin routes are local-only"}}), 403
        expected_token = app.config.get("ADMIN_TOKEN")
        provided_token = (
            request.headers.get("X-ChatMock-Admin-Token")
            or request.headers.get("X-Admin-Token")
            or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        )
        if isinstance(expected_token, str) and expected_token:
            if provided_token != expected_token:
                return jsonify({"error": {"message": "Invalid admin token"}}), 403
        return None

    @app.get("/admin/prompts")
    def admin_prompts_state():
        denied = _require_local_admin()
        if denied is not None:
            return denied
        return jsonify(prompt_manager.as_dict())

    @app.post("/admin/prompts/reload")
    def admin_prompts_reload():
        denied = _require_local_admin()
        if denied is not None:
            return denied
        try:
            prompt_manager.reload()
        except (FileNotFoundError, ValueError, OSError, PermissionError) as exc:
            return jsonify({"error": {"message": str(exc)}}), 400
        return jsonify(prompt_manager.as_dict())

    @app.post("/admin/prompts/config")
    def admin_prompts_config():
        denied = _require_local_admin()
        if denied is not None:
            return denied
        try:
            payload = request.get_json(silent=False)
        except BadRequest:
            return jsonify({"error": {"message": "Invalid JSON body"}}), 400
        if not isinstance(payload, dict):
            return jsonify({"error": {"message": "Invalid JSON body"}}), 400
        try:
            prompt_manager.update_config(payload)
        except (FileNotFoundError, ValueError, OSError, PermissionError) as exc:
            return jsonify({"error": {"message": str(exc)}}), 400
        return jsonify(prompt_manager.as_dict())

    @app.after_request
    def _cors(resp):
        for k, v in build_cors_headers().items():
            resp.headers.setdefault(k, v)
        return resp

    app.register_blueprint(openai_bp)
    app.register_blueprint(ollama_bp)
    sock = Sock(app)
    register_websocket_routes(sock)

    return app
