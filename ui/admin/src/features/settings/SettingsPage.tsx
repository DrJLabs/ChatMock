import { useState, type ReactNode } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type SettingsPageProps = {
  uiSection: ReactNode;
  behaviorSection: ReactNode;
  aboutSection: ReactNode;
};

export function SettingsPage({ uiSection, behaviorSection, aboutSection }: SettingsPageProps) {
  const [tab, setTab] = useState<"ui" | "behavior" | "about">("ui");

  return (
    <Tabs className="page-grid" onValueChange={(value) => setTab(value as "ui" | "behavior" | "about")} value={tab}>
      <div className="mode-header-card">
        <div>
          <p className="eyebrow">Settings</p>
          <h2>Control browser-local preferences without changing live runtime config.</h2>
          <p className="muted">Theme and code/font size are local to this browser until you apply them.</p>
        </div>
        <TabsList aria-label="Settings sections" className="segmented-control">
          <TabsTrigger className="segment-button" value="ui">
            UI
          </TabsTrigger>
          <TabsTrigger className="segment-button" value="behavior">
            Behavior
          </TabsTrigger>
          <TabsTrigger className="segment-button" value="about">
            About
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="ui">{uiSection}</TabsContent>
      <TabsContent value="behavior">{behaviorSection}</TabsContent>
      <TabsContent value="about">{aboutSection}</TabsContent>
    </Tabs>
  );
}
