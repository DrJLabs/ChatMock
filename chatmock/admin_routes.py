from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from .config import _read_prompt_text, write_prompt_texts_atomically

admin_bp = Blueprint("admin", __name__)


def _default_admin_ui_dist_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "ui" / "admin" / "dist"


def _resolve_admin_ui_dist_dir() -> Path:
    configured = current_app.config.get("ADMIN_UI_DIST_DIR")
    if isinstance(configured, Path):
        return configured
    if isinstance(configured, str) and configured.strip():
        return Path(configured)
    return _default_admin_ui_dist_dir()


def _require_local_admin():
    callback = current_app.config.get("REQUIRE_LOCAL_ADMIN")
    if callable(callback):
        return callback()
    return jsonify({"error": {"message": "Admin auth callback unavailable"}}), 500


def _get_instance_service():
    callback = current_app.config.get("GET_INSTANCE_SERVICE")
    if callable(callback):
        return callback()
    raise RuntimeError("Instance service callback unavailable")


def _get_draft_service():
    callback = current_app.config.get("GET_DRAFT_SERVICE")
    if callable(callback):
        return callback()
    raise RuntimeError("Draft service callback unavailable")


def _registry_error(exc: Exception):
    callback = current_app.config.get("REGISTRY_ERROR_HANDLER")
    if callable(callback):
        return callback(exc)
    return jsonify({"error": {"message": str(exc)}}), 400


def _resolve_repo_root() -> Path:
    configured = current_app.config.get("REPO_ROOT")
    if isinstance(configured, Path):
        return configured
    if isinstance(configured, str) and configured.strip():
        return Path(configured)
    return Path(__file__).resolve().parent.parent


def _resolve_prompt_file_path(raw_path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("Prompt file path must be a non-empty string")
    repo_root = _resolve_repo_root().resolve()
    candidate = Path(raw_path)
    resolved = (repo_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"Prompt file path must stay within repo root: {raw_path}") from exc
    return resolved


def _build_prompt_file_payload(base_prompt_path: str, codex_prompt_path: str, *, reloaded_current_prompt_set: bool) -> dict[str, Any]:
    base_path = _resolve_prompt_file_path(base_prompt_path)
    codex_path = _resolve_prompt_file_path(codex_prompt_path)
    return {
        "base_prompt_path": base_prompt_path,
        "codex_prompt_path": codex_prompt_path,
        "base_prompt_text": _read_prompt_text(base_path),
        "codex_prompt_text": _read_prompt_text(codex_path),
        "reloaded_current_prompt_set": reloaded_current_prompt_set,
    }


def _read_json_body() -> dict[str, Any]:
    try:
        payload = request.get_json(silent=False)
    except (BadRequest, UnsupportedMediaType) as exc:
        raise ValueError("Invalid JSON body") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid JSON body")
    return payload


def _serve_admin_ui_path(path: str = ""):
    denied = _require_local_admin()
    if denied is not None:
        return denied

    dist_dir = _resolve_admin_ui_dist_dir()
    if not dist_dir.is_dir():
        return jsonify({"error": {"message": f"Admin UI build not found: {dist_dir}"}}), 404

    normalized_path = path.strip("/")
    if normalized_path:
        asset_path = dist_dir / normalized_path
        if asset_path.is_file():
            return send_from_directory(dist_dir, normalized_path)

    index_path = dist_dir / "index.html"
    if not index_path.is_file():
        return jsonify({"error": {"message": f"Admin UI index not found: {index_path}"}}), 404
    return send_from_directory(dist_dir, "index.html")


@admin_bp.get("/admin/ui")
@admin_bp.get("/admin/ui/")
def admin_ui_index():
    return _serve_admin_ui_path()


@admin_bp.get("/admin/ui/<path:path>")
def admin_ui_path(path: str):
    return _serve_admin_ui_path(path)


@admin_bp.get("/admin/prompts")
def admin_prompts_state():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    prompt_manager = current_app.config["PROMPT_MANAGER"]
    return jsonify(prompt_manager.as_dict())


@admin_bp.post("/admin/prompts/reload")
def admin_prompts_reload():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    prompt_manager = current_app.config["PROMPT_MANAGER"]
    try:
        prompt_manager.reload()
    except (FileNotFoundError, ValueError, OSError, PermissionError) as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
    return jsonify(prompt_manager.as_dict())


@admin_bp.post("/admin/prompts/config")
def admin_prompts_config():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    prompt_manager = current_app.config["PROMPT_MANAGER"]
    try:
        payload = _read_json_body()
        prompt_manager.update_config(payload)
    except (FileNotFoundError, ValueError, OSError, PermissionError) as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
    return jsonify(prompt_manager.as_dict())


@admin_bp.post("/admin/prompts/files/read")
def admin_prompt_files_read():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        payload = _read_json_body()
        base_prompt_path = str(payload["base_prompt_path"])
        codex_prompt_path = str(payload["codex_prompt_path"])
        return jsonify(
            _build_prompt_file_payload(
                base_prompt_path,
                codex_prompt_path,
                reloaded_current_prompt_set=False,
            )
        )
    except (FileNotFoundError, KeyError, OSError, PermissionError, ValueError) as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@admin_bp.post("/admin/prompts/files/write")
def admin_prompt_files_write():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        payload = _read_json_body()
        base_prompt_path = str(payload["base_prompt_path"])
        codex_prompt_path = str(payload["codex_prompt_path"])
        base_prompt_text = payload["base_prompt_text"]
        codex_prompt_text = payload["codex_prompt_text"]
        base_path = _resolve_prompt_file_path(base_prompt_path)
        codex_path = _resolve_prompt_file_path(codex_prompt_path)
        write_prompt_texts_atomically(
            [
                (base_path, base_prompt_text),
                (codex_path, codex_prompt_text),
            ]
        )

        prompt_manager = current_app.config["PROMPT_MANAGER"]
        current_state = prompt_manager.get_state()
        should_reload = (
            current_state.base_prompt_path == str(base_path)
            or current_state.codex_prompt_path == str(codex_path)
        )
        if should_reload:
            prompt_manager.reload()

        return jsonify(
            _build_prompt_file_payload(
                base_prompt_path,
                codex_prompt_path,
                reloaded_current_prompt_set=should_reload,
            )
        )
    except (FileNotFoundError, KeyError, OSError, PermissionError, ValueError) as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@admin_bp.get("/admin/profiles")
def admin_profiles():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_instance_service()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify({"profiles": service.list_profiles()})


@admin_bp.get("/admin/instances")
def admin_instances():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_instance_service()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify({"instances": service.list_instances()})


@admin_bp.get("/admin/instances/<instance_id>/preview")
def admin_instance_preview(instance_id: str):
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_instance_service()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    try:
        preview = service.render_instance_preview(instance_id)
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc)}}), 404
    return jsonify(preview)


@admin_bp.get("/admin/draft")
def admin_draft_state():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_draft_service()
    except RuntimeError as exc:
        return _registry_error(exc)
    return jsonify(service.get_draft())


@admin_bp.post("/admin/draft/reset")
def admin_draft_reset():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_draft_service()
        current_app.config["INSTANCE_SERVICE"] = None
        return jsonify(service.reset())
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)


@admin_bp.post("/admin/draft/validate")
def admin_draft_validate():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_draft_service()
    except RuntimeError as exc:
        return _registry_error(exc)
    return jsonify(service.validate())


@admin_bp.post("/admin/draft/preview")
def admin_draft_preview():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_draft_service()
    except RuntimeError as exc:
        return _registry_error(exc)
    return jsonify(service.preview())


@admin_bp.post("/admin/draft/apply")
def admin_draft_apply():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        service = _get_draft_service()
        result = service.apply()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    current_app.config["INSTANCE_SERVICE"] = None
    return jsonify(result)


@admin_bp.post("/admin/profiles")
def admin_create_profile():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        payload = _read_json_body()
        draft = _get_draft_service().create_profile(payload)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify(draft), 201


@admin_bp.put("/admin/profiles/<profile_id>")
def admin_update_profile(profile_id: str):
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        payload = _read_json_body()
        draft = _get_draft_service().update_profile(profile_id, payload)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify(draft)


@admin_bp.delete("/admin/profiles/<profile_id>")
def admin_delete_profile(profile_id: str):
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        draft = _get_draft_service().delete_profile(profile_id)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify(draft)


@admin_bp.post("/admin/instances")
def admin_create_instance():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        payload = _read_json_body()
        draft = _get_draft_service().create_instance(payload)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify(draft), 201


@admin_bp.put("/admin/instances/<instance_id>")
def admin_update_instance(instance_id: str):
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        payload = _read_json_body()
        draft = _get_draft_service().update_instance(instance_id, payload)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify(draft)


@admin_bp.delete("/admin/instances/<instance_id>")
def admin_delete_instance(instance_id: str):
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        draft = _get_draft_service().delete_instance(instance_id)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify(draft)


@admin_bp.post("/admin/runtime/validate")
def admin_runtime_validate():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    try:
        summary = _get_instance_service().validate_registries()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    return jsonify(summary)


@admin_bp.post("/admin/runtime/prompts/reload")
def admin_runtime_prompts_reload():
    return admin_prompts_reload()


@admin_bp.post("/admin/runtime/redeploy")
def admin_runtime_redeploy():
    denied = _require_local_admin()
    if denied is not None:
        return denied
    callback = current_app.config.get("RUNTIME_REDEPLOY_CALLBACK")
    if callable(callback):
        result = callback()
        if isinstance(result, dict):
            return jsonify(result)
    return jsonify({"ok": True, "status": "noop"})
