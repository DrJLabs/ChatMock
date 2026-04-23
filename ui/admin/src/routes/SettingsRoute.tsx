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
            <p className="muted">UI settings shell.</p>
          </article>
        </section>
      }
      behaviorSection={<BehaviorSettingsSection />}
      aboutSection={<AboutSettingsSection />}
    />
  );
}
