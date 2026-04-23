import { fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { beforeEach, describe, expect, it } from "vitest";

import { UISettingsProvider, useUISettings } from "./provider";

function Harness() {
  const {
    appliedSettings,
    draftSettings,
    setDraftThemeId,
    setDraftCodeScale,
    applyUISettingsDraft,
    resetUISettingsDraft,
  } = useUISettings();

  return (
    <div>
      <span data-testid="applied-theme">{appliedSettings.themeId}</span>
      <span data-testid="applied-scale">{appliedSettings.codeScale}</span>
      <span data-testid="draft-theme">{draftSettings.themeId}</span>
      <span data-testid="draft-scale">{draftSettings.codeScale}</span>
      <button onClick={() => setDraftThemeId("midnight")}>preview theme</button>
      <button onClick={() => setDraftCodeScale(113)}>preview scale 113</button>
      <button onClick={() => setDraftCodeScale(121)}>preview scale 121</button>
      <button onClick={() => void applyUISettingsDraft()}>apply</button>
      <button onClick={() => resetUISettingsDraft()}>reset</button>
    </div>
  );
}

function TechnicalTextProbe() {
  return (
    <div>
      <textarea className="technical-text" data-testid="technical-text" defaultValue="SELECT * FROM records;" />
      <code data-testid="plain-code" style={{ fontSize: "16px" }}>
        plain code
      </code>
    </div>
  );
}

function getStylesheetText() {
  return Array.from(document.head.querySelectorAll("style"))
    .map((style) => style.textContent ?? "")
    .join("\n");
}

describe("UISettingsProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.dataset.theme = "";
    document.documentElement.style.removeProperty("--admin-code-scale");
    document.head.innerHTML = "";

    const style = document.createElement("style");
    style.textContent = readFileSync("src/styles.css", "utf8");
    document.head.append(style);
  });

  it("normalizes draft state immediately and restores applied values on reset", () => {
    render(
      <UISettingsProvider>
        <Harness />
      </UISettingsProvider>,
    );

    fireEvent.click(screen.getByText("preview scale 113"));

    expect(screen.getByTestId("draft-scale")).toHaveTextContent("115");
    expect(screen.getByTestId("applied-scale")).toHaveTextContent("100");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("115");

    fireEvent.click(screen.getByText("reset"));

    expect(screen.getByTestId("draft-scale")).toHaveTextContent("100");
    expect(screen.getByTestId("applied-scale")).toHaveTextContent("100");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("100");
  });

  it("keeps draft, applied, document root, and storage aligned after apply", () => {
    window.localStorage.setItem(
      "chatmock.admin.ui-settings",
      JSON.stringify({ themeId: "midnight", codeScale: 113 }),
    );

    render(
      <UISettingsProvider>
        <Harness />
      </UISettingsProvider>,
    );

    fireEvent.click(screen.getByText("preview theme"));
    fireEvent.click(screen.getByText("preview scale 121"));

    expect(screen.getByTestId("draft-theme")).toHaveTextContent("midnight");
    expect(screen.getByTestId("draft-scale")).toHaveTextContent("120");
    expect(screen.getByTestId("applied-theme")).toHaveTextContent("midnight");
    expect(screen.getByTestId("applied-scale")).toHaveTextContent("115");
    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");

    fireEvent.click(screen.getByText("apply"));

    expect(screen.getByTestId("applied-theme")).toHaveTextContent("midnight");
    expect(screen.getByTestId("applied-scale")).toHaveTextContent("120");
    expect(screen.getByTestId("draft-scale")).toHaveTextContent("120");
    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
    expect(window.localStorage.getItem("chatmock.admin.ui-settings")).toContain("\"codeScale\":120");
  });

  it("applies theme and code scale styles to the document root", () => {
    render(
      <UISettingsProvider>
        <Harness />
      </UISettingsProvider>,
    );

    fireEvent.click(screen.getByText("preview theme"));
    fireEvent.click(screen.getByText("preview scale 121"));

    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
  });

  it("scales technical text without rescaling every code block", () => {
    render(
      <UISettingsProvider>
        <Harness />
        <TechnicalTextProbe />
      </UISettingsProvider>,
    );

    fireEvent.click(screen.getByText("preview theme"));
    fireEvent.click(screen.getByText("preview scale 121"));

    const technicalText = screen.getByTestId("technical-text");
    const plainCode = screen.getByTestId("plain-code");
    const stylesheetText = getStylesheetText();

    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
    expect(technicalText).toHaveClass("technical-text");
    expect(plainCode).not.toHaveClass("technical-text");
    expect(stylesheetText).toMatch(/\.technical-text,\s*\.prompt-textarea,\s*\.preview-card code,\s*\.advanced-card code/);
    expect(stylesheetText).not.toContain("code { font-size: calc(0.875rem * (var(--admin-code-scale) / 100))");
  });
});
