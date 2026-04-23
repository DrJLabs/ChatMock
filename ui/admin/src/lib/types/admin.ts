export type Profile = {
  id: string;
  label: string;
  description: string;
  prompt_dir: string;
  base_prompt_path: string;
  codex_prompt_path: string;
  runtime_defaults: {
    inject_default_instructions: boolean;
  };
  ui: {
    order: number;
    editable: boolean;
  };
};

export type Instance = {
  id: string;
  label: string;
  profile_id: string;
  bind_host: string;
  port: number;
  runtime: string;
  prompt_config_path: string;
  state_group: string;
  compose_service_name: string;
  container_name: string;
  env_overrides: Record<string, string>;
  env_prefix?: string | null;
  healthcheck: {
    path: string;
  };
  ui: {
    order: number;
    mutable_fields: string[];
  };
  enabled: boolean;
};

export type DraftState = {
  profiles: Profile[];
  instances: Instance[];
  dirty: boolean;
  last_loaded_at: number;
};

export type ValidationSummary = {
  ok: boolean;
  errors: string[];
  profiles: string[];
  instances: string[];
};

export type InstancePreview = {
  instance: {
    id: string;
    label: string;
    profile_id: string;
    compose_service_name: string;
    container_name: string;
    bind_host: string;
    port: number;
    runtime: string;
    state_group: string;
    enabled: boolean;
  };
  profile: {
    id: string;
    prompt_dir: string;
    base_prompt_path: string;
    codex_prompt_path: string;
  };
  runtime: {
    environment: Record<string, string>;
    volumes: string[];
    healthcheck_path: string;
  };
  validation: {
    ok: boolean;
    errors: string[];
  };
};

export type DraftPreview = {
  ok: boolean;
  validation: ValidationSummary;
  dirty: boolean;
  instance_previews: InstancePreview[];
  compose_preview: {
    services: Record<
      string,
      {
        container_name: string;
        bind: string;
        profile_id: string;
        prompt_config_path: string;
      }
    >;
    state_groups: Record<string, string[]>;
  };
};

export type PromptState = {
  prompt_dir: string;
  base_prompt_path: string;
  codex_prompt_path: string;
  base_prompt_text: string;
  codex_prompt_text: string;
  prompt_config_path?: string | null;
};

export type PromptFilePayload = {
  base_prompt_path: string;
  codex_prompt_path: string;
  base_prompt_text: string;
  codex_prompt_text: string;
  reloaded_current_prompt_set: boolean;
};

export type ProfilesResponse = { profiles: Profile[] };
export type InstancesResponse = { instances: Instance[] };
export type RuntimeRedeployResponse = { ok: boolean; status: string };
