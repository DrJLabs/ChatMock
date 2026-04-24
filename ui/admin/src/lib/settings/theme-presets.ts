import { THEME_IDS, type ThemeId } from "./types";

export type ThemePreset = {
  id: ThemeId;
  label: string;
  description: string;
  previewClassName: string;
};

const THEME_PRESET_DEFINITIONS: Record<ThemeId, Omit<ThemePreset, "id">> = {
  obsidian: {
    label: "Obsidian",
    description: "Neutral dark console with low-glare contrast.",
    previewClassName: "theme-obsidian",
  },
  midnight: {
    label: "Midnight",
    description: "Blue-black operator theme with deeper accents.",
    previewClassName: "theme-midnight",
  },
  blueprint: {
    label: "Blueprint",
    description: "Cool dark theme with stronger steel-blue surfaces.",
    previewClassName: "theme-blueprint",
  },
  "high-contrast": {
    label: "High Contrast",
    description: "Sharper separation for brighter text and borders.",
    previewClassName: "theme-high-contrast",
  },
};

export const THEME_PRESETS: ThemePreset[] = THEME_IDS.map((id) => ({
  id,
  ...THEME_PRESET_DEFINITIONS[id],
}));
