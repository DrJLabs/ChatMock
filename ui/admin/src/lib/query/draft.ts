import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiJson } from "@/lib/api/client";
import type { DraftPreview, DraftState, ValidationSummary } from "@/lib/types/admin";

import { adminMutationKeys, adminQueryKeys } from "./keys";

async function invalidateCurrentState(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: adminQueryKeys.profiles }),
    queryClient.invalidateQueries({ queryKey: adminQueryKeys.instances }),
    queryClient.invalidateQueries({ queryKey: adminQueryKeys.runtimeValidation }),
    queryClient.invalidateQueries({ queryKey: adminQueryKeys.prompts }),
  ]);
}

export function useDraftStateQuery() {
  return useQuery({
    queryKey: adminQueryKeys.draft,
    queryFn: () => apiGet<DraftState>("/admin/draft"),
  });
}

export function useDraftMutations() {
  const queryClient = useQueryClient();

  async function syncDraftAndRefreshCurrentState(draft: DraftState) {
    queryClient.setQueryData(adminQueryKeys.draft, draft);
    await invalidateCurrentState(queryClient);
  }

  return {
    validateDraft: useMutation({
      mutationKey: adminMutationKeys.draft,
      mutationFn: () => apiJson<ValidationSummary>("/admin/draft/validate", "POST"),
    }),
    previewDraft: useMutation({
      mutationKey: adminMutationKeys.draft,
      mutationFn: () => apiJson<DraftPreview>("/admin/draft/preview", "POST"),
    }),
    applyDraft: useMutation({
      mutationKey: adminMutationKeys.draft,
      mutationFn: () => apiJson<DraftState>("/admin/draft/apply", "POST"),
      onSuccess: syncDraftAndRefreshCurrentState,
    }),
    resetDraft: useMutation({
      mutationKey: adminMutationKeys.draft,
      mutationFn: () => apiJson<DraftState>("/admin/draft/reset", "POST"),
      onSuccess: syncDraftAndRefreshCurrentState,
    }),
  };
}
