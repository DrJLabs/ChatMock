from __future__ import annotations

import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CLIENT_ID_DEFAULT = os.getenv("CHATGPT_LOCAL_CLIENT_ID") or "app_EMoamEEZ73f0CkXaXp7hrann"
OAUTH_ISSUER_DEFAULT = os.getenv("CHATGPT_LOCAL_ISSUER") or "https://auth.openai.com"
OAUTH_TOKEN_URL = f"{OAUTH_ISSUER_DEFAULT}/oauth/token"

CHATGPT_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


def prompt_state_home() -> Path:
    home = os.getenv("CHATGPT_LOCAL_HOME") or os.getenv("CODEX_HOME")
    if not home:
        home = os.path.expanduser("~/.chatgpt-local")
    return Path(home)


def default_prompt_config_path() -> Path:
    override = os.getenv("CHATGPT_LOCAL_PROMPT_CONFIG")
    if isinstance(override, str) and override.strip():
        return Path(override.strip())
    return prompt_state_home() / "prompt-config.json"


def _candidate_prompt_paths(filename: str) -> list[Path]:
    return [
        Path(__file__).parent.parent / filename,
        Path(__file__).parent / filename,
        Path(getattr(sys, "_MEIPASS", "")) / filename if getattr(sys, "_MEIPASS", None) else None,
        Path.cwd() / filename,
    ]


def _read_prompt_text(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"Prompt file {path} is empty")
    return content


@dataclass(frozen=True)
class PromptConfigState:
    prompt_dir: str | None
    base_prompt_path: str
    codex_prompt_path: str
    loaded_at: float


class PromptManager:
    def __init__(
        self,
        *,
        prompt_dir: str | None = None,
        base_prompt_path: str | None = None,
        codex_prompt_path: str | None = None,
        prompt_config_path: str | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._config_path = Path(prompt_config_path) if prompt_config_path else default_prompt_config_path()
        self._state: PromptConfigState | None = None
        self._base_instructions = ""
        self._codex_instructions = ""
        self._initial_defaults = {
            "prompt_dir": prompt_dir,
            "base_prompt_path": base_prompt_path,
            "codex_prompt_path": codex_prompt_path,
        }
        self.reload()

    def _resolve_legacy_defaults(self) -> dict[str, str | None]:
        explicit_prompt_dir = os.getenv("CHATGPT_LOCAL_PROMPT_DIR")
        explicit_base = os.getenv("CHATGPT_LOCAL_PROMPT_BASE_PATH")
        explicit_codex = os.getenv("CHATGPT_LOCAL_PROMPT_CODEX_PATH")
        if isinstance(explicit_prompt_dir, str) and explicit_prompt_dir.strip():
            return self._normalize_config({"prompt_dir": explicit_prompt_dir.strip()})
        if isinstance(explicit_base, str) and explicit_base.strip():
            return self._normalize_config(
                {
                    "base_prompt_path": explicit_base.strip(),
                    "codex_prompt_path": explicit_codex.strip() if isinstance(explicit_codex, str) and explicit_codex.strip() else None,
                }
            )

        for candidate in _candidate_prompt_paths("prompt.md"):
            if not candidate:
                continue
            codex_candidate = candidate.with_name("prompt_gpt5_codex.md")
            if candidate.exists():
                return self._normalize_config(
                    {
                        "prompt_dir": str(candidate.parent),
                        "base_prompt_path": str(candidate),
                        "codex_prompt_path": str(codex_candidate if codex_candidate.exists() else candidate),
                    }
                )
        raise FileNotFoundError("Failed to locate prompt.md via env, package paths, or CWD.")

    def _load_persisted_config(self) -> dict[str, Any] | None:
        if not self._config_path.exists():
            return None
        data = json.loads(self._config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Prompt config at {self._config_path} is not a JSON object")
        return data

    def _normalize_config(self, config: dict[str, Any]) -> dict[str, str | None]:
        prompt_dir = config.get("prompt_dir")
        base_prompt_path = config.get("base_prompt_path")
        codex_prompt_path = config.get("codex_prompt_path")

        normalized_dir = str(Path(prompt_dir).expanduser()) if isinstance(prompt_dir, str) and prompt_dir.strip() else None
        normalized_base = str(Path(base_prompt_path).expanduser()) if isinstance(base_prompt_path, str) and base_prompt_path.strip() else None
        normalized_codex = str(Path(codex_prompt_path).expanduser()) if isinstance(codex_prompt_path, str) and codex_prompt_path.strip() else None

        if normalized_dir:
            normalized_base = normalized_base or str(Path(normalized_dir) / "prompt.md")
            normalized_codex = normalized_codex or str(Path(normalized_dir) / "prompt_gpt5_codex.md")

        if not normalized_base:
            raise ValueError("Prompt config requires prompt_dir or base_prompt_path")
        if not normalized_codex:
            normalized_codex = normalized_base

        base_path = Path(normalized_base)
        codex_path = Path(normalized_codex)
        if not base_path.exists():
            raise FileNotFoundError(f"Base prompt file not found: {base_path}")
        if not codex_path.exists():
            raise FileNotFoundError(f"Codex prompt file not found: {codex_path}")
        _read_prompt_text(base_path)
        _read_prompt_text(codex_path)

        return {
            "prompt_dir": normalized_dir,
            "base_prompt_path": str(base_path),
            "codex_prompt_path": str(codex_path),
        }

    def _write_config(self, config: dict[str, str | None]) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "prompt_dir": config.get("prompt_dir"),
            "base_prompt_path": config["base_prompt_path"],
            "codex_prompt_path": config["codex_prompt_path"],
        }
        self._config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def reload(self) -> PromptConfigState:
        with self._lock:
            persisted = self._load_persisted_config()
            if persisted is None:
                seed = {k: v for k, v in self._initial_defaults.items() if isinstance(v, str) and v.strip()}
                if seed:
                    normalized = self._normalize_config(seed)
                else:
                    normalized = self._resolve_legacy_defaults()
                self._write_config(normalized)
            else:
                normalized = self._normalize_config(persisted)
            base_text = _read_prompt_text(Path(normalized["base_prompt_path"]))
            codex_text = _read_prompt_text(Path(normalized["codex_prompt_path"]))
            self._base_instructions = base_text
            self._codex_instructions = codex_text
            self._state = PromptConfigState(
                prompt_dir=normalized.get("prompt_dir"),
                base_prompt_path=normalized["base_prompt_path"],
                codex_prompt_path=normalized["codex_prompt_path"],
                loaded_at=time.time(),
            )
            return self._state

    def update_config(self, config: dict[str, Any]) -> PromptConfigState:
        with self._lock:
            current = self.get_state()
            prompt_dir = config.get("prompt_dir", current.prompt_dir)
            if "prompt_dir" in config and "base_prompt_path" not in config:
                base_prompt_path = None
            else:
                base_prompt_path = config.get("base_prompt_path", current.base_prompt_path)
            if "prompt_dir" in config and "codex_prompt_path" not in config:
                codex_prompt_path = None
            else:
                codex_prompt_path = config.get("codex_prompt_path", current.codex_prompt_path)
            merged = {
                "prompt_dir": prompt_dir,
                "base_prompt_path": base_prompt_path,
                "codex_prompt_path": codex_prompt_path,
            }
            normalized = self._normalize_config(merged)
            self._write_config(normalized)
            return self.reload()

    def get_state(self) -> PromptConfigState:
        with self._lock:
            if self._state is None:
                return self.reload()
            return self._state

    def get_base_instructions(self) -> str:
        with self._lock:
            if not self._base_instructions:
                self.reload()
            return self._base_instructions

    def get_codex_instructions(self) -> str:
        with self._lock:
            if not self._codex_instructions:
                self.reload()
            return self._codex_instructions

    def as_dict(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "prompt_dir": state.prompt_dir,
            "base_prompt_path": state.base_prompt_path,
            "codex_prompt_path": state.codex_prompt_path,
            "loaded_at": state.loaded_at,
            "prompt_config_path": str(self._config_path),
        }


_PROMPT_MANAGER: PromptManager | None = None


def get_prompt_manager(
    *,
    prompt_dir: str | None = None,
    base_prompt_path: str | None = None,
    codex_prompt_path: str | None = None,
    prompt_config_path: str | None = None,
    reset: bool = False,
) -> PromptManager:
    global _PROMPT_MANAGER
    if reset or _PROMPT_MANAGER is None:
        _PROMPT_MANAGER = PromptManager(
            prompt_dir=prompt_dir,
            base_prompt_path=base_prompt_path,
            codex_prompt_path=codex_prompt_path,
            prompt_config_path=prompt_config_path,
        )
    return _PROMPT_MANAGER


def read_base_instructions() -> str:
    return get_prompt_manager().get_base_instructions()


def read_gpt5_codex_instructions(fallback: str) -> str:
    content = get_prompt_manager().get_codex_instructions()
    return content if isinstance(content, str) and content.strip() else fallback


BASE_INSTRUCTIONS = read_base_instructions()
GPT5_CODEX_INSTRUCTIONS = read_gpt5_codex_instructions(BASE_INSTRUCTIONS)
