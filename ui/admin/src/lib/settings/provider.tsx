import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import {
  loadAppliedUISettings,
  normalizeUISettings,
  saveAppliedUISettings,
} from "./storage";
import { DEFAULT_UI_SETTINGS, type ThemeId, type UISettings } from "./types";

type UISettingsContextValue = {
  appliedSettings: UISettings;
  draftSettings: UISettings;
  isDirty: boolean;
  setDraftThemeId: (themeId: ThemeId) => void;
  setDraftCodeScale: (codeScale: number) => void;
  applyUISettingsDraft: () => void;
  resetUISettingsDraft: () => void;
};

const UISettingsContext = createContext<UISettingsContextValue | null>(null);

function applySettingsToDocument(settings: UISettings): void {
  document.documentElement.dataset.theme = settings.themeId;
  document.documentElement.style.setProperty("--admin-code-scale", String(settings.codeScale));
}

export function UISettingsProvider({ children }: PropsWithChildren) {
  const [appliedSettings, setAppliedSettings] = useState<UISettings>(() => {
    if (typeof window === "undefined") {
      return DEFAULT_UI_SETTINGS;
    }

    return loadAppliedUISettings();
  });
  const [draftSettings, setDraftSettings] = useState<UISettings>(appliedSettings);

  useEffect(() => {
    applySettingsToDocument(draftSettings);
  }, [draftSettings]);

  const setDraftThemeId = useCallback((themeId: ThemeId) => {
    setDraftSettings((current) => normalizeUISettings({ ...current, themeId }));
  }, []);

  const setDraftCodeScale = useCallback((codeScale: number) => {
    setDraftSettings((current) => normalizeUISettings({ ...current, codeScale }));
  }, []);

  const applyUISettingsDraft = useCallback(() => {
    const next = normalizeUISettings(draftSettings);

    setAppliedSettings(next);
    setDraftSettings(next);
    saveAppliedUISettings(next);
  }, [draftSettings]);

  const resetUISettingsDraft = useCallback(() => {
    setDraftSettings(appliedSettings);
  }, [appliedSettings]);

  const value = useMemo<UISettingsContextValue>(
    () => ({
      appliedSettings,
      draftSettings,
      isDirty:
        appliedSettings.themeId !== draftSettings.themeId ||
        appliedSettings.codeScale !== draftSettings.codeScale,
      setDraftThemeId,
      setDraftCodeScale,
      applyUISettingsDraft,
      resetUISettingsDraft,
    }),
    [appliedSettings, draftSettings, setDraftThemeId, setDraftCodeScale, applyUISettingsDraft, resetUISettingsDraft],
  );

  return <UISettingsContext.Provider value={value}>{children}</UISettingsContext.Provider>;
}

export function seedUISettingsDocument(): void {
  if (typeof document === "undefined") {
    return;
  }

  applySettingsToDocument(loadAppliedUISettings());
}

export function useUISettings(): UISettingsContextValue {
  const value = useContext(UISettingsContext);

  if (value == null) {
    throw new Error("useUISettings must be used inside UISettingsProvider.");
  }

  return value;
}
