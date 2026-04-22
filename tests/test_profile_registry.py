from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chatmock.profile_registry import load_profiles


BARE_PROFILE_YAML = """\
id: bare
label: Bare
description: Default low-opinion prompt set for the main ChatMock service
prompt_dir: prompts/bare
base_prompt_file: prompt.md
codex_prompt_file: prompt_gpt5_codex.md
runtime_defaults:
  inject_default_instructions: true
ui:
  order: 10
  editable: true
"""


CLAWMEM_PROFILE_YAML = """\
id: clawmem
label: ClawMem
description: ClawMem-specific prompt set for the secondary managed service
prompt_dir: prompts/clawmem
base_prompt_file: prompt.md
codex_prompt_file: prompt_gpt5_codex.md
runtime_defaults:
  inject_default_instructions: true
ui:
  order: 20
  editable: true
"""


class ProfileRegistryTests(unittest.TestCase):
    def _write_prompt_set(self, root: Path, profile: str) -> None:
        prompt_dir = root / "prompts" / profile
        prompt_dir.mkdir(parents=True, exist_ok=True)
        (prompt_dir / "prompt.md").write_text(f"{profile} base", encoding="utf-8")
        (prompt_dir / "prompt_gpt5_codex.md").write_text(f"{profile} codex", encoding="utf-8")

    def test_load_profiles_returns_bare_and_clawmem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_prompt_set(root, "bare")
            self._write_prompt_set(root, "clawmem")
            config_root = root / "config" / "profiles"
            config_root.mkdir(parents=True, exist_ok=True)
            (config_root / "bare.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")
            (config_root / "clawmem.yaml").write_text(CLAWMEM_PROFILE_YAML, encoding="utf-8")

            profiles = load_profiles(config_root, repo_root=root)

            self.assertEqual([profile["id"] for profile in profiles], ["bare", "clawmem"])

    def test_duplicate_profile_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_prompt_set(root, "bare")
            config_root = root / "config" / "profiles"
            config_root.mkdir(parents=True, exist_ok=True)
            (config_root / "a.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")
            (config_root / "b.yaml").write_text(BARE_PROFILE_YAML, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate profile id: bare"):
                load_profiles(config_root, repo_root=root)
