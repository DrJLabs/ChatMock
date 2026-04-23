import type { Instance, Profile } from "@/lib/types/admin";

export type InstanceFormValues = {
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
  env_prefix: string;
  healthcheck_path: string;
  mutable_fields: string;
  ui_order: number;
  enabled: boolean;
};

export function buildNewInstanceFormValues(instances: Instance[], profiles: Profile[]): InstanceFormValues {
  const nextOrder = (instances[instances.length - 1]?.ui.order ?? 0) + 10;

  return {
    id: "",
    label: "New Instance",
    profile_id: profiles[0]?.id ?? "bare",
    bind_host: "127.0.0.1",
    port: 8000,
    runtime: "docker_compose",
    prompt_config_path: "/data/prompt-config-new.json",
    state_group: "shared-auth-default",
    compose_service_name: "",
    container_name: "",
    env_overrides: {},
    env_prefix: "",
    healthcheck_path: "/health",
    mutable_fields: "profile_id, port",
    ui_order: nextOrder,
    enabled: true,
  };
}

export function instanceToFormValues(instance: Instance): InstanceFormValues {
  return {
    id: instance.id,
    label: instance.label,
    profile_id: instance.profile_id,
    bind_host: instance.bind_host,
    port: instance.port,
    runtime: instance.runtime,
    prompt_config_path: instance.prompt_config_path,
    state_group: instance.state_group,
    compose_service_name: instance.compose_service_name,
    container_name: instance.container_name,
    env_overrides: instance.env_overrides,
    env_prefix: instance.env_prefix ?? "",
    healthcheck_path: instance.healthcheck.path,
    mutable_fields: instance.ui.mutable_fields.join(", "),
    ui_order: instance.ui.order,
    enabled: instance.enabled,
  };
}

export function formValuesToInstance(values: InstanceFormValues): Instance {
  return {
    id: values.id.trim(),
    label: values.label.trim(),
    profile_id: values.profile_id,
    bind_host: values.bind_host.trim(),
    port: Number.isFinite(values.port) ? values.port : 0,
    runtime: values.runtime,
    prompt_config_path: values.prompt_config_path.trim(),
    state_group: values.state_group.trim(),
    compose_service_name: values.compose_service_name.trim(),
    container_name: values.container_name.trim(),
    env_overrides: values.env_overrides,
    env_prefix: values.env_prefix.trim() || null,
    healthcheck: {
      path: values.healthcheck_path.trim(),
    },
    ui: {
      order: Number.isFinite(values.ui_order) ? values.ui_order : 0,
      mutable_fields: values.mutable_fields
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    },
    enabled: values.enabled,
  };
}
