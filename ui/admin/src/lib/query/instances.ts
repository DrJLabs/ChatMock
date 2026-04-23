import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiJson } from "@/lib/api/client";
import type {
  DraftState,
  Instance,
  InstancePreview,
  InstancesResponse,
  Profile,
} from "@/lib/types/admin";

import { adminMutationKeys, adminQueryKeys } from "./keys";
import { buildInstancePayload } from "./shared";

export function useInstancesQuery() {
  return useQuery({
    queryKey: adminQueryKeys.instances,
    queryFn: () => apiGet<InstancesResponse>("/admin/instances"),
    select: (response) => response.instances,
  });
}

export function useCurrentPreviewsQuery(instances: Instance[]) {
  const instanceIds = instances.map((instance) => instance.id);

  return useQuery({
    queryKey: adminQueryKeys.currentPreviews(instanceIds),
    queryFn: async () => {
      if (instances.length === 0) {
        return [] satisfies InstancePreview[];
      }

      const settled = await Promise.allSettled(
        instances.map((instance) => apiGet<InstancePreview>(`/admin/instances/${instance.id}/preview`)),
      );
      return settled.flatMap((result) => (result.status === "fulfilled" ? [result.value] : []));
    },
  });
}

export function useInstanceMutations() {
  const queryClient = useQueryClient();

  function syncDraft(draft: DraftState) {
    queryClient.setQueryData(adminQueryKeys.draft, draft);
  }

  return {
    saveInstance: useMutation({
      mutationKey: adminMutationKeys.instances,
      mutationFn: ({ instanceId, instance }: { instanceId: string; instance: Instance }) =>
        apiJson<DraftState>(`/admin/instances/${instanceId}`, "PUT", buildInstancePayload(instance)),
      onSuccess: syncDraft,
    }),
    createInstance: useMutation({
      mutationKey: adminMutationKeys.instances,
      mutationFn: (instance: Instance) =>
        apiJson<DraftState>("/admin/instances", "POST", buildInstancePayload(instance)),
      onSuccess: syncDraft,
    }),
    deleteInstance: useMutation({
      mutationKey: adminMutationKeys.instances,
      mutationFn: (instanceId: string) => apiJson<DraftState>(`/admin/instances/${instanceId}`, "DELETE"),
      onSuccess: syncDraft,
    }),
  };
}
