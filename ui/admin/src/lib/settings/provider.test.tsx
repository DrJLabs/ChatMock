import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { UISettingsProvider, useUISettings } from "./provider";

function Harness() {
  const {
    appliedSettings,
    draftSettings,
    setDraftThemeId,
    setDraftCodeScale,
    applyDraft,
    resetDraft,
  } = useUISettings();

  return (
    <div>
      <span data-testid="applied-theme">{appliedSettings.themeId}</span>
      <span data-testid="draft-theme">{draftSettings.themeId}</span>
      <span data-testid="draft-scale">{draftSettings.codeScale}</span>
      <button onClick={() => setDraftThemeId("midnight")}>preview theme</button>
      <button onClick={() => setDraftCodeScale(120)}>preview scale</button>
      <button onClick={() => void applyDraft()}>apply</button>
      <button onClick={() => resetDraft()}>reset</button>
    </div>
  );
}

describe("UISettingsProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.dataset.theme = "";
    document.documentElement.style.removeProperty("--admin-code-scale");
  });

  it("previews immediately but only persists on apply", () => {
    render(
      <UISettingsProvider>
        <Harness />
      </UISettingsProvider>,
    );

    fireEvent.click(screen.getByText("preview theme"));
    fireEvent.click(screen.getByText("preview scale"));

    expect(screen.getByTestId("draft-theme")).toHaveTextContent("midnight");
    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
    expect(screen.getByTestId("applied-theme")).toHaveTextContent("obsidian");

    fireEvent.click(screen.getByText("apply"));

    expect(screen.getByTestId("applied-theme")).toHaveTextContent("midnight");
    expect(window.localStorage.getItem("chatmock.admin.ui-settings")).toContain("midnight");
  });

  it("restores applied values on reset", () => {
    render(
      <UISettingsProvider>
        <Harness />
      </UISettingsProvider>,
    );

    fireEvent.click(screen.getByText("preview theme"));
    fireEvent.click(screen.getByText("reset"));

    expect(screen.getByTestId("draft-theme")).toHaveTextContent("obsidian");
    expect(document.documentElement.dataset.theme).toBe("obsidian");
  });
});
