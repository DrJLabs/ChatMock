import { fireEvent, render, screen } from "@testing-library/react";
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
    expect(screen.getByRole("tabpanel")).toHaveTextContent("UI shell content");

    fireEvent.click(screen.getByRole("tab", { name: "Behavior" }));

    expect(await screen.findByText("Behavior shell content")).toBeInTheDocument();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Behavior shell content");

    fireEvent.click(screen.getByRole("tab", { name: "About" }));

    expect(await screen.findByText("About shell content")).toBeInTheDocument();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("About shell content");
  });
});
