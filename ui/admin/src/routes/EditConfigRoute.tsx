import { useAdminApp } from "../App";
import { EditConfigPage } from "../features/edit-config/EditConfigPage";

export function EditConfigRoute() {
  const {
    profiles,
    instances,
    draft,
    busy,
    saveProfile,
    createProfile,
    deleteProfile,
    saveInstance,
    createInstance,
    deleteInstance,
  } = useAdminApp();

  return (
    <EditConfigPage
      profiles={draft?.profiles ?? profiles}
      instances={draft?.instances ?? instances}
      busy={busy}
      onSaveProfile={saveProfile}
      onCreateProfile={createProfile}
      onDeleteProfile={deleteProfile}
      onSaveInstance={saveInstance}
      onCreateInstance={createInstance}
      onDeleteInstance={deleteInstance}
    />
  );
}
