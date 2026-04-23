import {
  CODE_SCALE_STEP,
  DEFAULT_UI_SETTINGS,
  MAX_CODE_SCALE,
  MIN_CODE_SCALE,
  THEME_IDS,
  UI_SETTINGS_STORAGE_KEY,
  type ThemeId,
  type UISettings,
} from "./types";

function isThemeId(value: unknown): value is ThemeId {
  return typeof value === "string" && THEME_IDS.includes(value as ThemeId);
}

function normalizeCodeScale(value: unknown): number {
  const raw = typeof value === "number" ? value : Number(value);

  if (!Number.isFinite(raw)) {
    return DEFAULT_UI_SETTINGS.codeScale;
  }

  if (raw < MIN_CODE_SCALE || raw > MAX_CODE_SCALE) {
    return DEFAULT_UI_SETTINGS.codeScale;
  }

  const rounded = Math.round(raw / CODE_SCALE_STEP) * CODE_SCALE_STEP;

  if (rounded < MIN_CODE_SCALE || rounded > MAX_CODE_SCALE) {
    return DEFAULT_UI_SETTINGS.codeScale;
  }

  return rounded;
}

export function normalizeUISettings(value: unknown): UISettings {
  if (typeof value !== "object" || value == null) {
    return DEFAULT_UI_SETTINGS;
  }

  const record = value as Partial<Record<keyof UISettings, unknown>>;

  return {
    themeId: isThemeId(record.themeId)
      ? record.themeId
      : DEFAULT_UI_SETTINGS.themeId,
    codeScale: normalizeCodeScale(record.codeScale),
  };
}

export function loadAppliedUISettings(): UISettings {
  const raw = window.localStorage.getItem(UI_SETTINGS_STORAGE_KEY);

  if (!raw) {
    return DEFAULT_UI_SETTINGS;
  }

  try {
    return normalizeUISettings(JSON.parse(raw));
  } catch {
    return DEFAULT_UI_SETTINGS;
  }
}

export function saveAppliedUISettings(settings: UISettings): void {
  window.localStorage.setItem(UI_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
}
