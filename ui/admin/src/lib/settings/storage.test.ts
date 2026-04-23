import { beforeEach, describe, expect, it } from "vitest";

import { loadAppliedUISettings, saveAppliedUISettings } from "./storage";
import { DEFAULT_UI_SETTINGS, UI_SETTINGS_STORAGE_KEY } from "./types";

describe("UI settings storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns defaults when storage is empty", () => {
    expect(loadAppliedUISettings()).toEqual(DEFAULT_UI_SETTINGS);
  });

  it("normalizes invalid persisted values back to defaults", () => {
    window.localStorage.setItem(
      UI_SETTINGS_STORAGE_KEY,
      JSON.stringify({ themeId: "unknown", codeScale: 500 }),
    );

    expect(loadAppliedUISettings()).toEqual(DEFAULT_UI_SETTINGS);
  });

  it("round-trips valid settings", () => {
    const next = { themeId: "obsidian", codeScale: 115 };

    saveAppliedUISettings(next);

    expect(loadAppliedUISettings()).toEqual(next);
  });
});
