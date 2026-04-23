import { useEffect, useRef } from "react";

import { AboutSettingsSection } from "../features/settings/AboutSettingsSection";
import { BehaviorSettingsSection } from "../features/settings/BehaviorSettingsSection";
import { SettingsPage } from "../features/settings/SettingsPage";
import { UISettingsSection } from "../features/settings/UISettingsSection";
import { useUISettings } from "../lib/settings/provider";

export function SettingsRoute() {
  const { resetUISettingsDraft } = useUISettings();
  const resetUISettingsDraftRef = useRef(resetUISettingsDraft);

  useEffect(() => {
    resetUISettingsDraftRef.current = resetUISettingsDraft;
  }, [resetUISettingsDraft]);

  useEffect(() => {
    return () => {
      resetUISettingsDraftRef.current();
    };
  }, []);

  return (
    <SettingsPage
      uiSection={<UISettingsSection />}
      behaviorSection={<BehaviorSettingsSection />}
      aboutSection={<AboutSettingsSection />}
    />
  );
}
