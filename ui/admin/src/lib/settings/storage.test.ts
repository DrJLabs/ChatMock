import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadAppliedUISettings, saveAppliedUISettings } from "./storage";
import { THEME_PRESETS } from "./theme-presets";
import { DEFAULT_UI_SETTINGS, THEME_IDS, UI_SETTINGS_STORAGE_KEY } from "./types";

describe("UI settings storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("returns defaults when storage is empty", () => {
    expect(loadAppliedUISettings()).toEqual(DEFAULT_UI_SETTINGS);
  });

  it("returns defaults when storage access fails", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage unavailable");
    });

    expect(loadAppliedUISettings()).toEqual(DEFAULT_UI_SETTINGS);
  });

  it("returns defaults when persisted JSON is malformed", () => {
    vi.spyOn(Storage.prototype, "getItem").mockReturnValue("{not-json");

    expect(loadAppliedUISettings()).toEqual(DEFAULT_UI_SETTINGS);
  });

  it("normalizes partial persisted values", () => {
    window.localStorage.setItem(
      UI_SETTINGS_STORAGE_KEY,
      JSON.stringify({ themeId: "midnight" }),
    );

    expect(loadAppliedUISettings()).toEqual({
      themeId: "midnight",
      codeScale: 100,
    });
  });

  it("canonicalizes settings before saving", () => {
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {});

    saveAppliedUISettings({ themeId: "midnight", codeScale: 113 });

    expect(setItemSpy).toHaveBeenCalledWith(
      UI_SETTINGS_STORAGE_KEY,
      JSON.stringify({ themeId: "midnight", codeScale: 115 }),
    );
  });

  it("returns defaults when saving fails", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota exceeded");
    });

    expect(() => {
      saveAppliedUISettings({ themeId: "obsidian", codeScale: 115 });
    }).not.toThrow();
  });

  it("keeps the theme catalog aligned with the theme ids", () => {
    expect(THEME_PRESETS.map((preset) => preset.id)).toEqual(THEME_IDS);
  });

  it("round-trips valid settings through save and load", () => {
    const next = { themeId: "obsidian", codeScale: 115 };

    saveAppliedUISettings(next);

    expect(loadAppliedUISettings()).toEqual(next);
  });
});
