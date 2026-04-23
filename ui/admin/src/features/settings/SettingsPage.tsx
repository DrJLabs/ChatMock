import { useState, type ReactNode } from "react";

type SettingsPageProps = {
  uiSection: ReactNode;
  behaviorSection: ReactNode;
  aboutSection: ReactNode;
};

export function SettingsPage({ uiSection, behaviorSection, aboutSection }: SettingsPageProps) {
  const [tab, setTab] = useState<"ui" | "behavior" | "about">("ui");

  return (
    <div className="page-grid">
      <div className="mode-header-card">
        <div>
          <p className="eyebrow">Settings</p>
          <h2>Browser-local settings</h2>
          <p className="muted">This shell organizes settings into separate sections for later work.</p>
        </div>
        <div aria-label="Settings sections" className="segmented-control" role="tablist">
          <button
            id="settings-ui-tab"
            aria-selected={tab === "ui"}
            className="segment-button"
            onClick={() => setTab("ui")}
            role="tab"
            type="button"
          >
            UI
          </button>
          <button
            id="settings-behavior-tab"
            aria-selected={tab === "behavior"}
            className="segment-button"
            onClick={() => setTab("behavior")}
            role="tab"
            type="button"
          >
            Behavior
          </button>
          <button
            id="settings-about-tab"
            aria-selected={tab === "about"}
            className="segment-button"
            onClick={() => setTab("about")}
            role="tab"
            type="button"
          >
            About
          </button>
        </div>
      </div>

      <section aria-labelledby="settings-ui-tab" hidden={tab !== "ui"} role="tabpanel">
        {uiSection}
      </section>
      <section aria-labelledby="settings-behavior-tab" hidden={tab !== "behavior"} role="tabpanel">
        {behaviorSection}
      </section>
      <section aria-labelledby="settings-about-tab" hidden={tab !== "about"} role="tabpanel">
        {aboutSection}
      </section>
    </div>
  );
}
