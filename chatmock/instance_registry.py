from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Any

import yaml


_INSTANCE_ID_RE = re.compile(r"^[a-z0-9-]+$")
_REQUIRED_KEYS = {
    "id",
    "label",
    "profile_id",
    "bind_host",
    "port",
    "runtime",
    "prompt_config_path",
    "state_group",
    "compose_service_name",
    "container_name",
    "env_overrides",
    "healthcheck",
    "ui",
    "enabled",
}
_ALLOWED_MUTABLE_FIELDS = {"profile_id", "port"}


def _load_yaml_object(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Instance config {path} must contain a YAML object")
    return data


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Instance field {key} must be a non-empty string")
    return value.strip()


def _normalize_instance(data: dict[str, Any], *, known_profile_ids: set[str]) -> dict[str, Any]:
    missing = sorted(_REQUIRED_KEYS.difference(data))
    if missing:
        raise ValueError(f"Instance config missing required keys: {', '.join(missing)}")

    instance_id = _require_string(data, "id")
    if not _INSTANCE_ID_RE.match(instance_id):
        raise ValueError(f"Invalid instance id: {instance_id}")

    profile_id = _require_string(data, "profile_id")
    if profile_id not in known_profile_ids:
        raise ValueError(f"Unknown profile_id: {profile_id}")

    bind_host = _require_string(data, "bind_host")
    try:
        ipaddress.ip_address(bind_host)
    except ValueError as exc:
        raise ValueError(f"Invalid bind_host: {bind_host}") from exc

    port = data.get("port")
    if type(port) is not int or not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port}")

    runtime = _require_string(data, "runtime")
    if runtime != "docker_compose":
        raise ValueError(f"Unsupported runtime: {runtime}")

    prompt_config_path = _require_string(data, "prompt_config_path")
    if not prompt_config_path.startswith("/data/"):
        raise ValueError(f"Instance prompt_config_path must start with /data/: {prompt_config_path}")

    env_overrides = data.get("env_overrides")
    if not isinstance(env_overrides, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in env_overrides.items()
    ):
        raise ValueError("Instance env_overrides must be a string-to-string mapping")

    healthcheck = data.get("healthcheck")
    if not isinstance(healthcheck, dict):
        raise ValueError("Instance field healthcheck must be a mapping")
    healthcheck_path = healthcheck.get("path")
    if not isinstance(healthcheck_path, str) or not healthcheck_path.strip():
        raise ValueError("Instance healthcheck.path must be a non-empty string")

    ui = data.get("ui")
    if not isinstance(ui, dict):
        raise ValueError("Instance field ui must be a mapping")
    if type(ui.get("order")) is not int:
        raise ValueError("Instance ui.order must be an integer")
    mutable_fields = ui.get("mutable_fields")
    if not isinstance(mutable_fields, list) or not all(
        isinstance(field, str) and field in _ALLOWED_MUTABLE_FIELDS for field in mutable_fields
    ):
        raise ValueError("Instance ui.mutable_fields must be a list containing only profile_id and port")

    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("Instance field enabled must be a boolean")
    env_prefix = data.get("env_prefix")
    if env_prefix is not None and (not isinstance(env_prefix, str) or not env_prefix.strip()):
        raise ValueError("Instance field env_prefix must be a non-empty string when provided")

    return {
        "id": instance_id,
        "label": _require_string(data, "label"),
        "profile_id": profile_id,
        "bind_host": bind_host,
        "port": port,
        "runtime": runtime,
        "prompt_config_path": prompt_config_path,
        "state_group": _require_string(data, "state_group"),
        "compose_service_name": _require_string(data, "compose_service_name"),
        "container_name": _require_string(data, "container_name"),
        "env_overrides": dict(env_overrides),
        "env_prefix": env_prefix.strip() if isinstance(env_prefix, str) else None,
        "healthcheck": {"path": healthcheck_path},
        "ui": {"order": ui["order"], "mutable_fields": list(mutable_fields)},
        "enabled": enabled,
    }


def load_instances(config_root: Path | str, *, known_profile_ids: set[str]) -> list[dict[str, Any]]:
    config_root_path = Path(config_root)
    if not config_root_path.exists() or not config_root_path.is_dir():
        raise FileNotFoundError(f"Instance config directory not found: {config_root_path}")

    instances: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_services: set[str] = set()
    seen_containers: set[str] = set()
    seen_targets: set[tuple[str, int]] = set()
    for path in sorted(config_root_path.glob("*.yaml")):
        instance = _normalize_instance(_load_yaml_object(path), known_profile_ids=known_profile_ids)
        instance_id = instance["id"]
        service_name = instance["compose_service_name"]
        container_name = instance["container_name"]
        bind_target = (instance["bind_host"], instance["port"])
        if instance_id in seen_ids:
            raise ValueError(f"Duplicate instance id: {instance_id}")
        if service_name in seen_services:
            raise ValueError(f"Duplicate compose service name: {service_name}")
        if container_name in seen_containers:
            raise ValueError(f"Duplicate container name: {container_name}")
        if bind_target in seen_targets:
            raise ValueError(f"Duplicate bind target: {bind_target[0]}:{bind_target[1]}")
        seen_ids.add(instance_id)
        seen_services.add(service_name)
        seen_containers.add(container_name)
        seen_targets.add(bind_target)
        instances.append(instance)
    return sorted(instances, key=lambda item: (item["ui"]["order"], item["id"]))
