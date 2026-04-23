from __future__ import annotations

import os
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .instance_registry import serialize_instance_config, validate_instances_data
from .instance_service import (
    InstanceService,
    _default_instances_root,
    _default_profiles_root,
    build_instance_service,
)
from .profile_registry import serialize_profile_config, validate_profiles_data


class AdminDraftService:
    def __init__(
        self,
        *,
        repo_root: Path | str,
        profiles_root: Path | str | None = None,
        instances_root: Path | str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.profiles_root = Path(profiles_root) if profiles_root is not None else _default_profiles_root(self.repo_root)
        self.instances_root = Path(instances_root) if instances_root is not None else _default_instances_root(self.repo_root)
        self._draft: dict[str, Any] | None = None

    def get_draft(self) -> dict[str, Any]:
        draft = self._ensure_draft()
        return deepcopy(draft)

    def reset(self) -> dict[str, Any]:
        service = build_instance_service(repo_root=self.repo_root)
        self._draft = {
            "profiles": service.list_profiles(),
            "instances": service.list_instances(),
            "dirty": False,
            "last_loaded_at": time.time(),
        }
        return self.get_draft()

    def update_profile(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any]:
        draft = self._ensure_draft()
        for index, profile in enumerate(draft["profiles"]):
            if profile["id"] != profile_id:
                continue
            updated = deepcopy(profile)
            updated.update(data)
            updated["id"] = profile_id
            draft["profiles"][index] = updated
            draft["dirty"] = True
            return self.get_draft()
        raise ValueError(f"Unknown profile id: {profile_id}")

    def create_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        draft = self._ensure_draft()
        profile_id = data.get("id")
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ValueError("Profile field id must be a non-empty string")
        if any(profile["id"] == profile_id for profile in draft["profiles"]):
            raise ValueError(f"Duplicate profile id: {profile_id}")
        draft["profiles"].append(deepcopy(data))
        draft["dirty"] = True
        return self.get_draft()

    def delete_profile(self, profile_id: str) -> dict[str, Any]:
        draft = self._ensure_draft()
        original_length = len(draft["profiles"])
        draft["profiles"] = [profile for profile in draft["profiles"] if profile["id"] != profile_id]
        if len(draft["profiles"]) == original_length:
            raise ValueError(f"Unknown profile id: {profile_id}")
        draft["dirty"] = True
        return self.get_draft()

    def update_instance(self, instance_id: str, data: dict[str, Any]) -> dict[str, Any]:
        draft = self._ensure_draft()
        for index, instance in enumerate(draft["instances"]):
            if instance["id"] != instance_id:
                continue
            updated = deepcopy(instance)
            updated.update(data)
            updated["id"] = instance_id
            draft["instances"][index] = updated
            draft["dirty"] = True
            return self.get_draft()
        raise ValueError(f"Unknown instance id: {instance_id}")

    def create_instance(self, data: dict[str, Any]) -> dict[str, Any]:
        draft = self._ensure_draft()
        instance_id = data.get("id")
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise ValueError("Instance field id must be a non-empty string")
        if any(instance["id"] == instance_id for instance in draft["instances"]):
            raise ValueError(f"Duplicate instance id: {instance_id}")
        draft["instances"].append(deepcopy(data))
        draft["dirty"] = True
        return self.get_draft()

    def delete_instance(self, instance_id: str) -> dict[str, Any]:
        draft = self._ensure_draft()
        original_length = len(draft["instances"])
        draft["instances"] = [instance for instance in draft["instances"] if instance["id"] != instance_id]
        if len(draft["instances"]) == original_length:
            raise ValueError(f"Unknown instance id: {instance_id}")
        draft["dirty"] = True
        return self.get_draft()

    def validate(self) -> dict[str, Any]:
        try:
            service = self._build_draft_service()
        except (FileNotFoundError, OSError, ValueError) as exc:
            return {"ok": False, "errors": [str(exc)], "profiles": [], "instances": []}
        return {
            "ok": True,
            "errors": [],
            "profiles": [profile["id"] for profile in service.list_profiles()],
            "instances": [instance["id"] for instance in service.list_instances()],
        }

    def preview(self) -> dict[str, Any]:
        validation = self.validate()
        draft = self._ensure_draft()
        if not validation["ok"]:
            return {
                "ok": False,
                "validation": validation,
                "dirty": draft["dirty"],
                "instance_previews": [],
                "compose_preview": {"services": {}, "state_groups": {}},
            }
        service = self._build_draft_service()
        return {
            "ok": True,
            "validation": validation,
            "dirty": draft["dirty"],
            "instance_previews": [service.render_instance_preview(item["id"]) for item in service.list_instances()],
            "compose_preview": service.render_compose_preview(),
        }

    def apply(self) -> dict[str, Any]:
        validation = self.validate()
        if not validation["ok"]:
            raise ValueError("; ".join(validation["errors"]))
        service = self._build_draft_service()
        self._write_yaml_directory(
            self.profiles_root,
            service.list_profiles(),
            serializer=serialize_profile_config,
        )
        self._write_yaml_directory(
            self.instances_root,
            service.list_instances(),
            serializer=serialize_instance_config,
        )
        return self.reset()

    def _ensure_draft(self) -> dict[str, Any]:
        if self._draft is None:
            self.reset()
        assert self._draft is not None
        return self._draft

    def _build_draft_service(self) -> InstanceService:
        draft = self._ensure_draft()
        normalized_profiles = validate_profiles_data(deepcopy(draft["profiles"]), repo_root=self.repo_root)
        normalized_instances = validate_instances_data(
            deepcopy(draft["instances"]),
            known_profile_ids={profile["id"] for profile in normalized_profiles},
        )
        return InstanceService(
            repo_root=self.repo_root,
            profiles=normalized_profiles,
            instances=normalized_instances,
        )

    def _write_yaml_directory(
        self,
        root: Path,
        items: list[dict[str, Any]],
        *,
        serializer,
    ) -> None:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root.parent) as temp_dir:
            temp_root = Path(temp_dir)
            expected_names: set[str] = set()
            for item in items:
                payload = serializer(item)
                filename = f'{item["id"]}.yaml'
                expected_names.add(filename)
                temp_path = temp_root / filename
                temp_path.write_text(
                    yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
                    encoding="utf-8",
                )
            for temp_path in temp_root.glob("*.yaml"):
                os.replace(temp_path, root / temp_path.name)
            for existing in root.glob("*.yaml"):
                if existing.name not in expected_names:
                    existing.unlink()
