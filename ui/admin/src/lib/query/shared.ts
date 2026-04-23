import type { Instance, Profile } from "@/lib/types/admin";

export function buildProfilePayload(profile: Profile): Profile {
  return {
    ...profile,
    prompt_dir: profile.prompt_dir.trim(),
    base_prompt_path: profile.base_prompt_path.trim(),
    codex_prompt_path: profile.codex_prompt_path.trim(),
  };
}

export function buildInstancePayload(instance: Instance): Instance {
  return {
    ...instance,
    bind_host: instance.bind_host.trim(),
    prompt_config_path: instance.prompt_config_path.trim(),
    state_group: instance.state_group.trim(),
    compose_service_name: instance.compose_service_name.trim(),
    container_name: instance.container_name.trim(),
    env_prefix: instance.env_prefix?.trim() || null,
    ui: {
      ...instance.ui,
      mutable_fields: instance.ui.mutable_fields.map((item) => item.trim()).filter(Boolean),
    },
  };
}

export function toErrorMessage(error: unknown): string {
  if (typeof error === "string") {
    try {
      const parsed = JSON.parse(error);
      if (
        typeof parsed === "object" &&
        parsed !== null &&
        "error" in parsed &&
        typeof parsed.error === "object" &&
        parsed.error !== null &&
        "message" in parsed.error &&
        typeof parsed.error.message === "string"
      ) {
        return parsed.error.message;
      }
    } catch {
      // Keep the original string when it is not JSON.
    }
    return error;
  }

  return error instanceof Error ? error.message : "Unknown error";
}
