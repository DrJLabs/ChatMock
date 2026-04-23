import { useState } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import type { Instance, Profile } from "../../lib/types/admin";
import { InstancesPage } from "../instances/InstancesPage";
import { ProfilesPage } from "../profiles/ProfilesPage";

type EditConfigPageProps = {
  profiles: Profile[];
  instances: Instance[];
  busy: boolean;
  onSaveProfile: (profileId: string, profile: Profile) => Promise<void>;
  onCreateProfile: (profile: Profile) => Promise<void>;
  onDeleteProfile: (profileId: string) => Promise<void>;
  onSaveInstance: (instanceId: string, instance: Instance) => Promise<void>;
  onCreateInstance: (instance: Instance) => Promise<void>;
  onDeleteInstance: (instanceId: string) => Promise<void>;
};

export function EditConfigPage({
  profiles,
  instances,
  busy,
  onSaveProfile,
  onCreateProfile,
  onDeleteProfile,
  onSaveInstance,
  onCreateInstance,
  onDeleteInstance,
}: EditConfigPageProps) {
  const [tab, setTab] = useState<"profiles" | "instances">("profiles");

  return (
    <Tabs className="page-grid" onValueChange={(value) => setTab(value as "profiles" | "instances")} value={tab}>
      <div className="mode-header-card">
        <div>
          <p className="eyebrow">Edit Config</p>
          <h2>Make structural YAML-backed changes without touching the live runtime yet.</h2>
          <p className="muted">Profile and instance edits stay in the in-memory draft until you apply them from Current State.</p>
        </div>
        <TabsList className="segmented-control" aria-label="Config editors">
          <TabsTrigger className="segment-button" value="profiles">
            Profiles
          </TabsTrigger>
          <TabsTrigger className="segment-button" value="instances">
            Instances
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="profiles">
        <ProfilesPage
          profiles={profiles}
          busy={busy}
          onSaveProfile={onSaveProfile}
          onCreateProfile={onCreateProfile}
          onDeleteProfile={onDeleteProfile}
        />
      </TabsContent>

      <TabsContent value="instances">
        <InstancesPage
          instances={instances}
          profiles={profiles}
          busy={busy}
          onSaveInstance={onSaveInstance}
          onCreateInstance={onCreateInstance}
          onDeleteInstance={onDeleteInstance}
        />
      </TabsContent>
    </Tabs>
  );
}
