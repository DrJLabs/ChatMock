import { AboutSettingsSection } from "../features/settings/AboutSettingsSection";
import { BehaviorSettingsSection } from "../features/settings/BehaviorSettingsSection";
import { SettingsPage } from "../features/settings/SettingsPage";

export function SettingsRoute() {
  return (
    <SettingsPage
      uiSection={
        <section className="page-grid">
          <article className="panel-card">
            <h3>UI</h3>
            <p className="muted">Theme and code size controls are added in the next task.</p>
          </article>
        </section>
      }
      behaviorSection={<BehaviorSettingsSection />}
      aboutSection={<AboutSettingsSection />}
    />
  );
}
