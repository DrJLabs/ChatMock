import { AboutSettingsSection } from "../features/settings/AboutSettingsSection";
import { BehaviorSettingsSection } from "../features/settings/BehaviorSettingsSection";
import { SettingsPage } from "../features/settings/SettingsPage";
import { UISettingsSection } from "../features/settings/UISettingsSection";

export function SettingsRoute() {
  return (
    <SettingsPage
      uiSection={<UISettingsSection />}
      behaviorSection={<BehaviorSettingsSection />}
      aboutSection={<AboutSettingsSection />}
    />
  );
}
