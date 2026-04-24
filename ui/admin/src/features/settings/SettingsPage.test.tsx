import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("switches between section panels from the tab navigation", async () => {
    render(
      <SettingsPage
        uiSection={<div>UI shell content</div>}
        behaviorSection={<div>Behavior shell content</div>}
        aboutSection={<div>About shell content</div>}
      />,
    );

    expect(screen.getByRole("tab", { name: "UI" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Behavior" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "About" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "UI" })).toHaveAttribute("data-state", "active");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("UI shell content");

    fireEvent.keyDown(screen.getByRole("tab", { name: "UI" }), { key: "ArrowRight" });

    expect(await screen.findByRole("tab", { name: "Behavior", selected: true })).toHaveAttribute("data-state", "active");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Behavior shell content");

    fireEvent.keyDown(screen.getByRole("tab", { name: "Behavior" }), { key: "ArrowRight" });

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "About" })).toHaveAttribute("aria-selected", "true");
    });
    expect(screen.getByRole("tab", { name: "About" })).toHaveAttribute("data-state", "active");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("About shell content");
  });
});
