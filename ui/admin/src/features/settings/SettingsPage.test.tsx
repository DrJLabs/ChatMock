import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { UISettingsProvider } from "../../lib/settings/provider";
import { SettingsPage } from "./SettingsPage";
import { UISettingsSection } from "./UISettingsSection";

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

describe("UISettingsSection", () => {
  it("previews theme and code size, then applies or resets them", () => {
    window.localStorage.removeItem("chatmock.admin.ui-settings");
    document.documentElement.dataset.theme = "";
    document.documentElement.style.removeProperty("--admin-code-scale");

    render(
      <UISettingsProvider>
        <UISettingsSection />
      </UISettingsProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Midnight" }));
    fireEvent.change(screen.getByLabelText("Code and prompt text size"), {
      target: { value: "120" },
    });

    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
    expect(screen.getByText("Previewing changes")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));

    expect(document.documentElement.dataset.theme).toBe("obsidian");

    fireEvent.click(screen.getByRole("button", { name: "Midnight" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(window.localStorage.getItem("chatmock.admin.ui-settings")).toContain("midnight");
  });
});
