import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InstancesPage } from "../instances/InstancesPage";
import { ProfilesPage } from "../profiles/ProfilesPage";

describe("admin config editor forms", () => {
  it("blocks creating a profile when the required id is blank", async () => {
    const onCreateProfile = vi.fn().mockResolvedValue(undefined);

    render(
      <ProfilesPage
        profiles={[
          {
            id: "bare",
            label: "Bare",
            description: "Default profile",
            prompt_dir: "prompts/bare",
            base_prompt_path: "prompts/bare/prompt.md",
            codex_prompt_path: "prompts/bare/prompt_gpt5_codex.md",
            runtime_defaults: { inject_default_instructions: true },
            ui: { order: 10, editable: true },
          },
        ]}
        busy={false}
        onSaveProfile={vi.fn().mockResolvedValue(undefined)}
        onCreateProfile={onCreateProfile}
        onDeleteProfile={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "New Profile" }));
    fireEvent.click(screen.getByRole("button", { name: "Create Draft Profile" }));

    expect(await screen.findByText("Profile ID is required.")).toBeInTheDocument();
    expect(onCreateProfile).not.toHaveBeenCalled();
  });

  it("blocks creating an instance when the required id is blank", async () => {
    const onCreateInstance = vi.fn().mockResolvedValue(undefined);

    render(
      <InstancesPage
        instances={[
          {
            id: "chatmock-default",
            label: "Default",
            profile_id: "bare",
            bind_host: "127.0.0.1",
            port: 8000,
            runtime: "docker_compose",
            prompt_config_path: "/data/prompt-config.json",
            state_group: "shared-auth-default",
            compose_service_name: "chatmock",
            container_name: "chatmock",
            env_overrides: {},
            env_prefix: null,
            healthcheck: { path: "/health" },
            ui: { order: 10, mutable_fields: ["profile_id", "port"] },
            enabled: true,
          },
        ]}
        profiles={[
          {
            id: "bare",
            label: "Bare",
            description: "Default profile",
            prompt_dir: "prompts/bare",
            base_prompt_path: "prompts/bare/prompt.md",
            codex_prompt_path: "prompts/bare/prompt_gpt5_codex.md",
            runtime_defaults: { inject_default_instructions: true },
            ui: { order: 10, editable: true },
          },
        ]}
        busy={false}
        onSaveInstance={vi.fn().mockResolvedValue(undefined)}
        onCreateInstance={onCreateInstance}
        onDeleteInstance={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "New Instance" }));
    fireEvent.click(screen.getByRole("button", { name: "Create Draft Instance" }));

    expect(await screen.findByText("Instance ID is required.")).toBeInTheDocument();
    expect(onCreateInstance).not.toHaveBeenCalled();
  });

  it("blocks creating an instance when the port is out of range", async () => {
    const onCreateInstance = vi.fn().mockResolvedValue(undefined);

    render(
      <InstancesPage
        instances={[
          {
            id: "chatmock-default",
            label: "Default",
            profile_id: "bare",
            bind_host: "127.0.0.1",
            port: 8000,
            runtime: "docker_compose",
            prompt_config_path: "/data/prompt-config.json",
            state_group: "shared-auth-default",
            compose_service_name: "chatmock",
            container_name: "chatmock",
            env_overrides: {},
            env_prefix: null,
            healthcheck: { path: "/health" },
            ui: { order: 10, mutable_fields: ["profile_id", "port"] },
            enabled: true,
          },
        ]}
        profiles={[
          {
            id: "bare",
            label: "Bare",
            description: "Default profile",
            prompt_dir: "prompts/bare",
            base_prompt_path: "prompts/bare/prompt.md",
            codex_prompt_path: "prompts/bare/prompt_gpt5_codex.md",
            runtime_defaults: { inject_default_instructions: true },
            ui: { order: 10, editable: true },
          },
        ]}
        busy={false}
        onSaveInstance={vi.fn().mockResolvedValue(undefined)}
        onCreateInstance={onCreateInstance}
        onDeleteInstance={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "New Instance" }));
    fireEvent.change(screen.getByLabelText("Instance ID"), { target: { value: "chatmock-new" } });
    fireEvent.change(screen.getByLabelText("Port"), { target: { value: "70000" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Draft Instance" }));

    expect(onCreateInstance).not.toHaveBeenCalled();
    expect(await screen.findByText("Port must be between 1 and 65535.")).toBeInTheDocument();
  });
});
