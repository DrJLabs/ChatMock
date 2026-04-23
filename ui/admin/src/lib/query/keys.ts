export const adminQueryKeys = {
  root: ["admin"] as const,
  profiles: ["admin", "profiles"] as const,
  instances: ["admin", "instances"] as const,
  currentPreviewsRoot: ["admin", "instances", "previews"] as const,
  currentPreviews: (instanceIds: string[]) =>
    ["admin", "instances", "previews", ...instanceIds] as const,
  draft: ["admin", "draft"] as const,
  runtimeValidation: ["admin", "runtime", "validation"] as const,
  prompts: ["admin", "prompts"] as const,
};

export const adminMutationKeys = {
  root: ["admin"] as const,
  profiles: ["admin", "profiles", "mutations"] as const,
  instances: ["admin", "instances", "mutations"] as const,
  draft: ["admin", "draft", "mutations"] as const,
  runtime: ["admin", "runtime", "mutations"] as const,
  runtimeValidate: ["admin", "runtime", "validate"] as const,
  runtimeRedeploy: ["admin", "runtime", "redeploy"] as const,
  prompts: ["admin", "prompts", "mutations"] as const,
};
