import { describe, expect, it } from "vitest";

import { formValuesToInstance } from "./instanceForm";

describe("instance form normalization", () => {
  it("rejects non-integer ports", () => {
    expect(() =>
      formValuesToInstance({
        id: "chatmock-new",
        label: "ChatMock New",
        profile_id: "bare",
        bind_host: "127.0.0.1",
        port: 1.5,
        runtime: "docker_compose",
        prompt_config_path: "/data/prompt-config-new.json",
        state_group: "shared-auth-default",
        compose_service_name: "chatmock-new",
        container_name: "chatmock-new",
        env_overrides: {},
        env_prefix: "",
        healthcheck_path: "/health",
        mutable_fields: "profile_id, port",
        ui_order: 10,
        enabled: true,
      }),
    ).toThrow("Port must be an integer between 1 and 65535.");
  });
});
