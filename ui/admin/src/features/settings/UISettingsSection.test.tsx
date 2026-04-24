import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { UISettingsProvider } from "../../lib/settings/provider";
import { UISettingsSection } from "./UISettingsSection";

describe("UISettingsSection", () => {
  afterEach(() => {
    window.localStorage.removeItem("chatmock.admin.ui-settings");
    document.documentElement.dataset.theme = "";
    document.documentElement.style.removeProperty("--admin-code-scale");
  });

  it("marks the current applied preset before any preview changes", () => {
    render(
      <UISettingsProvider>
        <UISettingsSection />
      </UISettingsProvider>,
    );

    const obsidian = screen.getByRole("button", { name: "Obsidian" });
    const midnight = screen.getByRole("button", { name: "Midnight" });

    expect(obsidian).toHaveAttribute("aria-pressed", "true");
    expect(obsidian).toHaveAttribute("data-active", "true");
    expect(obsidian).toHaveAttribute("data-applied", "true");
    expect(midnight).toHaveAttribute("aria-pressed", "false");
    expect(midnight).toHaveAttribute("data-active", "false");
    expect(midnight).toHaveAttribute("data-applied", "false");
    expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reset" })).toBeDisabled();
    expect(screen.getByText("Applied settings are active.")).toBeInTheDocument();
  });

  it("keeps preview state separate and restores applied values on reset", () => {
    render(
      <UISettingsProvider>
        <UISettingsSection />
      </UISettingsProvider>,
    );

    const obsidian = screen.getByRole("button", { name: "Obsidian" });
    const midnight = screen.getByRole("button", { name: "Midnight" });
    const applyButton = screen.getByRole("button", { name: "Apply" });
    const resetButton = screen.getByRole("button", { name: "Reset" });

    fireEvent.click(midnight);
    fireEvent.change(screen.getByLabelText("Code and prompt text size"), {
      target: { value: "120" },
    });

    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
    expect(screen.getByText("Previewing changes")).toBeInTheDocument();
    expect(midnight).toHaveAttribute("aria-pressed", "true");
    expect(midnight).toHaveAttribute("data-active", "true");
    expect(midnight).toHaveAttribute("data-applied", "false");
    expect(obsidian).toHaveAttribute("data-active", "false");
    expect(obsidian).toHaveAttribute("data-applied", "true");
    expect(applyButton).toBeEnabled();
    expect(resetButton).toBeEnabled();

    fireEvent.click(resetButton);

    expect(document.documentElement.dataset.theme).toBe("obsidian");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("100");
    expect(screen.getByText("Applied settings are active.")).toBeInTheDocument();
    expect(obsidian).toHaveAttribute("aria-pressed", "true");
    expect(obsidian).toHaveAttribute("data-active", "true");
    expect(obsidian).toHaveAttribute("data-applied", "true");
    expect(midnight).toHaveAttribute("aria-pressed", "false");
    expect(midnight).toHaveAttribute("data-active", "false");
    expect(midnight).toHaveAttribute("data-applied", "false");
    expect(applyButton).toBeDisabled();
    expect(resetButton).toBeDisabled();
  });

  it("persists the applied preview state after apply", () => {
    render(
      <UISettingsProvider>
        <UISettingsSection />
      </UISettingsProvider>,
    );

    const obsidian = screen.getByRole("button", { name: "Obsidian" });
    const midnight = screen.getByRole("button", { name: "Midnight" });
    const applyButton = screen.getByRole("button", { name: "Apply" });

    fireEvent.click(midnight);
    fireEvent.change(screen.getByLabelText("Code and prompt text size"), {
      target: { value: "120" },
    });
    fireEvent.click(applyButton);

    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
    expect(JSON.parse(window.localStorage.getItem("chatmock.admin.ui-settings") ?? "{}")).toEqual({
      themeId: "midnight",
      codeScale: 120,
    });
    expect(midnight).toHaveAttribute("aria-pressed", "true");
    expect(midnight).toHaveAttribute("data-active", "true");
    expect(midnight).toHaveAttribute("data-applied", "true");
    expect(obsidian).toHaveAttribute("data-active", "false");
    expect(obsidian).toHaveAttribute("data-applied", "false");
  });
});
