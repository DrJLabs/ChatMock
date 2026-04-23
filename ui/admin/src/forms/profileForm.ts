import type { Profile } from "@/lib/types/admin";

export type ProfileFormValues = {
  id: string;
  label: string;
  description: string;
  prompt_dir: string;
  base_prompt_path: string;
  codex_prompt_path: string;
  inject_default_instructions: boolean;
  ui_order: number;
  editable: boolean;
};

export function buildNewProfileFormValues(profiles: Profile[]): ProfileFormValues {
  const nextOrder = (profiles[profiles.length - 1]?.ui.order ?? 0) + 10;

  return {
    id: "",
    label: "New Profile",
    description: "",
    prompt_dir: "prompts/bare",
    base_prompt_path: "prompts/bare/prompt.md",
    codex_prompt_path: "prompts/bare/prompt_gpt5_codex.md",
    inject_default_instructions: true,
    ui_order: nextOrder,
    editable: true,
  };
}

export function profileToFormValues(profile: Profile): ProfileFormValues {
  return {
    id: profile.id,
    label: profile.label,
    description: profile.description,
    prompt_dir: profile.prompt_dir,
    base_prompt_path: profile.base_prompt_path,
    codex_prompt_path: profile.codex_prompt_path,
    inject_default_instructions: profile.runtime_defaults.inject_default_instructions,
    ui_order: profile.ui.order,
    editable: profile.ui.editable,
  };
}

export function formValuesToProfile(values: ProfileFormValues): Profile {
  return {
    id: values.id.trim(),
    label: values.label.trim(),
    description: values.description,
    prompt_dir: values.prompt_dir.trim(),
    base_prompt_path: values.base_prompt_path.trim(),
    codex_prompt_path: values.codex_prompt_path.trim(),
    runtime_defaults: {
      inject_default_instructions: values.inject_default_instructions,
    },
    ui: {
      order: Number.isFinite(values.ui_order) ? values.ui_order : 0,
      editable: values.editable,
    },
  };
}
