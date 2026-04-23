import type { ThemeId } from "./types";

export type ThemePreset = {
  id: ThemeId;
  label: string;
  description: string;
  previewClassName: string;
};

export const THEME_PRESETS: ThemePreset[] = [
  {
    id: "obsidian",
    label: "Obsidian",
    description: "Neutral dark console with low-glare contrast.",
    previewClassName: "theme-obsidian",
  },
  {
    id: "midnight",
    label: "Midnight",
    description: "Blue-black operator theme with deeper accents.",
    previewClassName: "theme-midnight",
  },
  {
    id: "blueprint",
    label: "Blueprint",
    description: "Cool dark theme with stronger steel-blue surfaces.",
    previewClassName: "theme-blueprint",
  },
  {
    id: "high-contrast",
    label: "High Contrast",
    description: "Sharper separation for brighter text and borders.",
    previewClassName: "theme-high-contrast",
  },
];
