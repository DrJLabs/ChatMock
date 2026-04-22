from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .instance_registry import load_instances
from .profile_registry import load_profiles


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_profiles_root(repo_root: Path) -> Path:
    source_root = repo_root / "config" / "profiles"
    if source_root.exists():
        return source_root
    return repo_root / "chatmock" / "bundled_config" / "profiles"


def _default_instances_root(repo_root: Path) -> Path:
    source_root = repo_root / "config" / "instances"
    if source_root.exists():
        return source_root
    return repo_root / "chatmock" / "bundled_config" / "instances"


@dataclass
class InstanceService:
    repo_root: Path
    profiles: list[dict[str, Any]]
    instances: list[dict[str, Any]]

    def list_profiles(self) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self.profiles]

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        for profile in self.profiles:
            if profile["id"] == profile_id:
                return deepcopy(profile)
        raise ValueError(f"Unknown profile id: {profile_id}")

    def list_instances(self) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self.instances]

    def get_instance(self, instance_id: str) -> dict[str, Any]:
        for instance in self.instances:
            if instance["id"] == instance_id:
                return deepcopy(instance)
        raise ValueError(f"Unknown instance id: {instance_id}")

    def validate_registries(self) -> dict[str, Any]:
        errors: list[str] = []
        profiles: list[dict[str, Any]] = []
        instances: list[dict[str, Any]] = []
        try:
            profiles = load_profiles(_default_profiles_root(self.repo_root), repo_root=self.repo_root)
        except (FileNotFoundError, OSError, ValueError) as exc:
            errors.append(str(exc))
        if not errors:
            try:
                instances = load_instances(
                    _default_instances_root(self.repo_root),
                    known_profile_ids={profile["id"] for profile in profiles},
                )
            except (FileNotFoundError, OSError, ValueError) as exc:
                errors.append(str(exc))
        return {
            "ok": not errors,
            "profiles": [item["id"] for item in profiles],
            "instances": [item["id"] for item in instances],
            "errors": errors,
        }

    def render_instance_preview(self, instance_id: str) -> dict[str, Any]:
        instance = self.get_instance(instance_id)
        profile = self.get_profile(instance["profile_id"])
        prompt_dir = profile["prompt_dir"].rsplit("/", 1)[-1]
        prompt_env_prefix = instance.get("env_prefix") or instance["id"].upper().replace("-", "_")

        return {
            "instance": {
                "id": instance["id"],
                "label": instance["label"],
                "profile_id": instance["profile_id"],
                "compose_service_name": instance["compose_service_name"],
                "container_name": instance["container_name"],
                "bind_host": instance["bind_host"],
                "port": instance["port"],
                "runtime": instance["runtime"],
                "state_group": instance["state_group"],
                "enabled": instance["enabled"],
            },
            "profile": {
                "id": profile["id"],
                "prompt_dir": profile["prompt_dir"],
                "base_prompt_path": profile["base_prompt_path"],
                "codex_prompt_path": profile["codex_prompt_path"],
            },
            "runtime": {
                "environment": {
                    f"{prompt_env_prefix}_PROMPT_DIR": f"/app/prompts/{prompt_dir}",
                    f"{prompt_env_prefix}_PROMPT_CONFIG": instance["prompt_config_path"],
                    "CHATGPT_LOCAL_HOME": "/data",
                },
                "volumes": [
                    "chatmock_data:/data",
                    "./prompts:/app/prompts:ro",
                ],
                "healthcheck_path": instance["healthcheck"]["path"],
            },
            "validation": {"ok": True, "errors": []},
        }

    def render_compose_preview(self) -> dict[str, Any]:
        services: dict[str, dict[str, Any]] = {}
        state_groups: dict[str, list[str]] = {}
        for instance in self.instances:
            services[instance["compose_service_name"]] = {
                "container_name": instance["container_name"],
                "bind": f'{instance["bind_host"]}:{instance["port"]}:8000',
                "profile_id": instance["profile_id"],
                "prompt_config_path": instance["prompt_config_path"],
            }
            state_groups.setdefault(instance["state_group"], []).append(instance["id"])
        return {"services": services, "state_groups": state_groups}


def build_instance_service(*, repo_root: Path | str | None = None) -> InstanceService:
    repo_root_path = Path(repo_root) if repo_root is not None else _default_repo_root()
    profiles = load_profiles(_default_profiles_root(repo_root_path), repo_root=repo_root_path)
    instances = load_instances(
        _default_instances_root(repo_root_path),
        known_profile_ids={profile["id"] for profile in profiles},
    )
    return InstanceService(repo_root=repo_root_path, profiles=profiles, instances=instances)
