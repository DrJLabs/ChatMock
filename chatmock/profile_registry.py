from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_PROFILE_ID_RE = re.compile(r"^[a-z0-9-]+$")
_REQUIRED_KEYS = {
    "id",
    "label",
    "description",
    "prompt_dir",
    "base_prompt_file",
    "codex_prompt_file",
    "runtime_defaults",
    "ui",
}


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _iter_yaml_entries(config_root: Any) -> list[Any]:
    return sorted(
        [entry for entry in config_root.iterdir() if entry.is_file() and entry.name.endswith(".yaml")],
        key=lambda entry: entry.name,
    )


def _load_yaml_object(path: Any) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Profile config {path} must contain a YAML object")
    return data


def _default_config_root(repo_root: Path | None) -> Any:
    if repo_root is not None:
        return repo_root / "config" / "profiles"
    return _package_root() / "bundled_config" / "profiles"


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Profile field {key} must be a non-empty string")
    return value.strip()


def _normalize_profile(data: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    missing = sorted(_REQUIRED_KEYS.difference(data))
    if missing:
        raise ValueError(f"Profile config missing required keys: {', '.join(missing)}")

    profile_id = _require_string(data, "id")
    label = _require_string(data, "label")
    description = _require_string(data, "description")
    if not _PROFILE_ID_RE.match(profile_id):
        raise ValueError(f"Invalid profile id: {profile_id}")

    prompt_dir = Path(_require_string(data, "prompt_dir"))
    if prompt_dir.is_absolute():
        raise ValueError(f"Profile prompt_dir must be repo-relative: {prompt_dir}")

    resolved_prompt_dir = repo_root / prompt_dir
    if not resolved_prompt_dir.exists() or not resolved_prompt_dir.is_dir():
        raise ValueError(f"Profile prompt_dir does not exist: {prompt_dir}")

    base_prompt_file = _require_string(data, "base_prompt_file")
    codex_prompt_file = _require_string(data, "codex_prompt_file")
    base_prompt_path = resolved_prompt_dir / base_prompt_file
    codex_prompt_path = resolved_prompt_dir / codex_prompt_file
    if not base_prompt_path.exists():
        raise ValueError(f"Base prompt file not found: {prompt_dir / base_prompt_file}")
    if not codex_prompt_path.exists():
        raise ValueError(f"Codex prompt file not found: {prompt_dir / codex_prompt_file}")

    runtime_defaults = data.get("runtime_defaults")
    if not isinstance(runtime_defaults, dict):
        raise ValueError("Profile field runtime_defaults must be a mapping")
    inject_default_instructions = runtime_defaults.get("inject_default_instructions")
    if not isinstance(inject_default_instructions, bool):
        raise ValueError("Profile runtime_defaults.inject_default_instructions must be a boolean")

    ui = data.get("ui")
    if not isinstance(ui, dict):
        raise ValueError("Profile field ui must be a mapping")
    if type(ui.get("order")) is not int:
        raise ValueError("Profile ui.order must be an integer")
    if not isinstance(ui.get("editable"), bool):
        raise ValueError("Profile ui.editable must be a boolean")

    return {
        "id": profile_id,
        "label": label,
        "description": description,
        "prompt_dir": prompt_dir.as_posix(),
        "base_prompt_path": (prompt_dir / base_prompt_file).as_posix(),
        "codex_prompt_path": (prompt_dir / codex_prompt_file).as_posix(),
        "runtime_defaults": {"inject_default_instructions": inject_default_instructions},
        "ui": {"order": ui["order"], "editable": ui["editable"]},
    }


def load_profiles(config_root: Path | str | None = None, *, repo_root: Path | str | None = None) -> list[dict[str, Any]]:
    repo_root_path = Path(repo_root) if repo_root is not None else None
    config_root_path = Path(config_root) if config_root is not None else _default_config_root(repo_root_path)
    if repo_root_path is None:
        repo_root_path = _default_repo_root() if (Path(_default_repo_root()) / "config" / "profiles").exists() else _package_root()

    profiles: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in _iter_yaml_entries(config_root_path):
        profile = _normalize_profile(_load_yaml_object(path), repo_root=repo_root_path)
        profile_id = profile["id"]
        if profile_id in seen_ids:
            raise ValueError(f"Duplicate profile id: {profile_id}")
        seen_ids.add(profile_id)
        profiles.append(profile)
    return sorted(profiles, key=lambda item: (item["ui"]["order"], item["id"]))
