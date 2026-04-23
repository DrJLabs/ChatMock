import { useNavigate } from "react-router";

import { useAdminApp } from "../App";
import { DashboardPage } from "../features/dashboard/DashboardPage";

export function CurrentStateRoute() {
  const navigate = useNavigate();
  const {
    profiles,
    instances,
    draft,
    runtimeValidation,
    prompts,
    currentPreviews,
    draftValidation,
    draftPreview,
    busy,
    reloadPrompts,
    validateRuntime,
    applyDraft,
    redeployRuntime,
    validateDraft,
    previewDraft,
    resetDraft,
  } = useAdminApp();

  return (
    <DashboardPage
      draft={draft}
      currentProfileCount={profiles.length}
      currentInstanceCount={instances.length}
      runtimeValidation={runtimeValidation}
      prompts={prompts}
      previews={currentPreviews}
      draftValidation={draftValidation}
      draftPreview={draftPreview}
      busy={busy}
      onNavigate={(page) => navigate(page === "prompt-files" ? "/prompt-files" : "/edit-config")}
      onReloadPrompts={reloadPrompts}
      onValidateRuntime={validateRuntime}
      onApplyDraft={applyDraft}
      onRedeploy={redeployRuntime}
      onValidateDraft={validateDraft}
      onPreviewDraft={previewDraft}
      onResetDraft={resetDraft}
    />
  );
}
