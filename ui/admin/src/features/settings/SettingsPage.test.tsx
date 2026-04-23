import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("renders the section shell with tab navigation", () => {
    render(
      <SettingsPage
        uiSection={<div>ui section</div>}
        behaviorSection={<div>Not configured yet.</div>}
        aboutSection={<div>Docs and build details live here.</div>}
      />,
    );

    expect(screen.getByText("Control browser-local preferences without changing live runtime config.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "UI" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Behavior" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "About" })).toBeInTheDocument();
    expect(screen.getByText("ui section")).toBeInTheDocument();
  });
});
