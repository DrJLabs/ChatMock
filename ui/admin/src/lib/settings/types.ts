export const UI_SETTINGS_STORAGE_KEY = "chatmock.admin.ui-settings";

export const THEME_IDS = [
  "obsidian",
  "midnight",
  "blueprint",
  "high-contrast",
] as const;

export type ThemeId = (typeof THEME_IDS)[number];

export type UISettings = {
  themeId: ThemeId;
  codeScale: number;
};

export const DEFAULT_UI_SETTINGS: UISettings = {
  themeId: "obsidian",
  codeScale: 100,
};

export const MIN_CODE_SCALE = 90;
export const MAX_CODE_SCALE = 130;
export const CODE_SCALE_STEP = 5;
