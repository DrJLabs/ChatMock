import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiJson } from "@/lib/api/client";
import type { RuntimeRedeployResponse, ValidationSummary } from "@/lib/types/admin";

import { adminMutationKeys, adminQueryKeys } from "./keys";

export function useRuntimeValidationQuery() {
  return useQuery({
    queryKey: adminQueryKeys.runtimeValidation,
    queryFn: () => apiJson<ValidationSummary>("/admin/runtime/validate", "POST"),
  });
}

export function useRuntimeMutations() {
  const queryClient = useQueryClient();

  return {
    validateRuntime: useMutation({
      mutationKey: adminMutationKeys.runtime,
      mutationFn: () => apiJson<ValidationSummary>("/admin/runtime/validate", "POST"),
      onSuccess: (summary) => {
        queryClient.setQueryData(adminQueryKeys.runtimeValidation, summary);
      },
    }),
    redeployRuntime: useMutation({
      mutationKey: adminMutationKeys.runtime,
      mutationFn: () => apiJson<RuntimeRedeployResponse>("/admin/runtime/redeploy", "POST"),
    }),
  };
}
