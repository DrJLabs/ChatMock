import { createContext, useContext, useMemo, useState } from "react";
import { useIsFetching, useIsMutating } from "@tanstack/react-query";
import { Outlet } from "react-router";

import {
  useDraftMutations,
  useDraftStateQuery,
} from "./lib/query/draft";
import { useCurrentPreviewsQuery, useInstanceMutations, useInstancesQuery } from "./lib/query/instances";
import { adminMutationKeys, adminQueryKeys } from "./lib/query/keys";
import { useProfileMutations, useProfilesQuery } from "./lib/query/profiles";
import { usePromptMutations, usePromptStateQuery } from "./lib/query/prompts";
import { useRuntimeMutations, useRuntimeValidationQuery } from "./lib/query/runtime";
import { toErrorMessage } from "./lib/query/shared";
import type {
  DraftPreview,
  DraftState,
  Instance,
  InstancePreview,
  Profile,
  PromptFilePayload,
  PromptState,
  RuntimeRedeployResponse,
  ValidationSummary,
} from "./lib/types/admin";

type AdminAppContextValue = {
  profiles: Profile[];
  instances: Instance[];
  draft: DraftState | null;
  runtimeValidation: ValidationSummary | null;
  draftValidation: ValidationSummary | null;
  draftPreview: DraftPreview | null;
  currentPreviews: InstancePreview[];
  prompts: PromptState | null;
  busy: boolean;
  error: string | null;
  notice: string | null;
  statusText: string;
  saveProfile: (profileId: string, profile: Profile) => Promise<void>;
  createProfile: (profile: Profile) => Promise<void>;
  deleteProfile: (profileId: string) => Promise<void>;
  saveInstance: (instanceId: string, instance: Instance) => Promise<void>;
  createInstance: (instance: Instance) => Promise<void>;
  deleteInstance: (instanceId: string) => Promise<void>;
  validateDraft: () => Promise<void>;
  previewDraft: () => Promise<void>;
  applyDraft: () => Promise<void>;
  resetDraft: () => Promise<void>;
  validateRuntime: () => Promise<void>;
  reloadPrompts: () => Promise<void>;
  redeployRuntime: () => Promise<RuntimeRedeployResponse | void>;
  loadPromptFiles: (payload: {
    base_prompt_path: string;
    codex_prompt_path: string;
  }) => Promise<PromptFilePayload>;
  savePromptFiles: (payload: PromptFilePayload) => Promise<PromptFilePayload>;
};

const AdminAppContext = createContext<AdminAppContextValue | null>(null);

function firstErrorMessage(errors: unknown[]): string | null {
  const match = errors.find((error) => error != null);
  return match == null ? null : toErrorMessage(match);
}

export function useAdminApp(): AdminAppContextValue {
  const value = useContext(AdminAppContext);

  if (value == null) {
    throw new Error("useAdminApp must be used inside the admin app provider.");
  }

  return value;
}

export default function App() {
  const profilesQuery = useProfilesQuery();
  const instancesQuery = useInstancesQuery();
  const draftQuery = useDraftStateQuery();
  const runtimeValidationQuery = useRuntimeValidationQuery();
  const promptStateQuery = usePromptStateQuery();
  const currentPreviewsQuery = useCurrentPreviewsQuery(instancesQuery.data ?? []);

  const profileMutations = useProfileMutations();
  const instanceMutations = useInstanceMutations();
  const draftMutations = useDraftMutations();
  const runtimeMutations = useRuntimeMutations();
  const promptMutations = usePromptMutations();

  const [draftValidation, setDraftValidation] = useState<ValidationSummary | null>(null);
  const [draftPreview, setDraftPreview] = useState<DraftPreview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchingCount = useIsFetching({ queryKey: adminQueryKeys.root });
  const mutatingCount = useIsMutating({ mutationKey: adminMutationKeys.root });

  const busy = fetchingCount > 0 || mutatingCount > 0;

  const error = firstErrorMessage([
    actionError,
    profilesQuery.error,
    instancesQuery.error,
    draftQuery.error,
    runtimeValidationQuery.error,
    promptStateQuery.error,
    currentPreviewsQuery.error,
  ]);

  const statusText = useMemo(() => {
    if (error) {
      return `Attention: ${error}`;
    }
    if (notice) {
      return notice;
    }
    return draftQuery.data?.dirty ? "Draft contains unapplied edits." : "Draft and runtime are in sync.";
  }, [draftQuery.data?.dirty, error, notice]);

  function clearDraftDerivedState() {
    setDraftValidation(null);
    setDraftPreview(null);
  }

  async function runAction<T>(message: string, action: () => Promise<T>): Promise<T> {
    try {
      setActionError(null);
      const result = await action();
      setNotice(message);
      return result;
    } catch (caught) {
      setActionError(toErrorMessage(caught));
      throw caught;
    }
  }

  async function saveProfile(profileId: string, profile: Profile) {
    clearDraftDerivedState();
    await runAction("Draft profile saved.", () =>
      profileMutations.saveProfile.mutateAsync({ profileId, profile }),
    );
  }

  async function createProfile(profile: Profile) {
    clearDraftDerivedState();
    await runAction("Draft profile created.", () => profileMutations.createProfile.mutateAsync(profile));
  }

  async function deleteProfile(profileId: string) {
    clearDraftDerivedState();
    await runAction("Draft profile removed.", () => profileMutations.deleteProfile.mutateAsync(profileId));
  }

  async function saveInstance(instanceId: string, instance: Instance) {
    clearDraftDerivedState();
    await runAction("Draft instance saved.", () =>
      instanceMutations.saveInstance.mutateAsync({ instanceId, instance }),
    );
  }

  async function createInstance(instance: Instance) {
    clearDraftDerivedState();
    await runAction("Draft instance created.", () => instanceMutations.createInstance.mutateAsync(instance));
  }

  async function deleteInstance(instanceId: string) {
    clearDraftDerivedState();
    await runAction("Draft instance removed.", () => instanceMutations.deleteInstance.mutateAsync(instanceId));
  }

  async function validateDraft() {
    const summary = await runAction("Draft validated.", () => draftMutations.validateDraft.mutateAsync());
    setDraftValidation(summary);
  }

  async function previewDraft() {
    const preview = await runAction("Draft preview refreshed.", () => draftMutations.previewDraft.mutateAsync());
    setDraftPreview(preview);
    setDraftValidation(preview.validation);
  }

  async function applyDraft() {
    await runAction("Draft applied to YAML.", () => draftMutations.applyDraft.mutateAsync());
    clearDraftDerivedState();
  }

  async function resetDraft() {
    await runAction("Draft reset to current config.", () => draftMutations.resetDraft.mutateAsync());
    clearDraftDerivedState();
  }

  async function validateRuntime() {
    await runAction("Runtime validation refreshed.", () => runtimeMutations.validateRuntime.mutateAsync());
  }

  async function reloadPrompts() {
    await runAction("Prompt files reloaded.", () => promptMutations.reloadPrompts.mutateAsync());
  }

  async function redeployRuntime() {
    return runAction("Redeploy requested.", () => runtimeMutations.redeployRuntime.mutateAsync());
  }

  async function loadPromptFiles(payload: { base_prompt_path: string; codex_prompt_path: string }) {
    return runAction("Prompt files loaded.", () => promptMutations.readPromptFiles.mutateAsync(payload));
  }

  async function savePromptFiles(payload: PromptFilePayload) {
    const result = await runAction("Prompt files saved.", () => promptMutations.writePromptFiles.mutateAsync(payload));
    return result.next;
  }

  return (
    <AdminAppContext.Provider
      value={{
        profiles: profilesQuery.data ?? [],
        instances: instancesQuery.data ?? [],
        draft: draftQuery.data ?? null,
        runtimeValidation: runtimeValidationQuery.data ?? null,
        draftValidation,
        draftPreview,
        currentPreviews: currentPreviewsQuery.data ?? [],
        prompts: promptStateQuery.data ?? null,
        busy,
        error,
        notice,
        statusText,
        saveProfile,
        createProfile,
        deleteProfile,
        saveInstance,
        createInstance,
        deleteInstance,
        validateDraft,
        previewDraft,
        applyDraft,
        resetDraft,
        validateRuntime,
        reloadPrompts,
        redeployRuntime,
        loadPromptFiles,
        savePromptFiles,
      }}
    >
      <Outlet />
    </AdminAppContext.Provider>
  );
}
