import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiJson } from "@/lib/api/client";
import type { PromptFilePayload, PromptState } from "@/lib/types/admin";

import { adminMutationKeys, adminQueryKeys } from "./keys";

export function usePromptStateQuery() {
  return useQuery({
    queryKey: adminQueryKeys.prompts,
    queryFn: () => apiGet<PromptState>("/admin/prompts"),
  });
}

export function usePromptMutations() {
  const queryClient = useQueryClient();

  return {
    reloadPrompts: useMutation({
      mutationKey: adminMutationKeys.prompts,
      mutationFn: () => apiJson<PromptState>("/admin/runtime/prompts/reload", "POST"),
      onSuccess: (promptState) => {
        queryClient.setQueryData(adminQueryKeys.prompts, promptState);
      },
    }),
    readPromptFiles: useMutation({
      mutationKey: adminMutationKeys.prompts,
      mutationFn: (payload: { base_prompt_path: string; codex_prompt_path: string }) =>
        apiJson<PromptFilePayload>("/admin/prompts/files/read", "POST", payload),
    }),
    writePromptFiles: useMutation({
      mutationKey: adminMutationKeys.prompts,
      mutationFn: async (payload: PromptFilePayload) => {
        const next = await apiJson<PromptFilePayload>("/admin/prompts/files/write", "POST", payload);
        try {
          const promptState = await apiGet<PromptState>("/admin/prompts");
          return { next, promptState };
        } catch {
          void queryClient.invalidateQueries({ queryKey: adminQueryKeys.prompts });
          return { next, promptState: undefined };
        }
      },
      onSuccess: ({ promptState }) => {
        if (promptState != null) {
          queryClient.setQueryData(adminQueryKeys.prompts, promptState);
        }
      },
    }),
  };
}
