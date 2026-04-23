import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiJson } from "@/lib/api/client";
import type { DraftState, Profile, ProfilesResponse } from "@/lib/types/admin";

import { adminMutationKeys, adminQueryKeys } from "./keys";
import { buildProfilePayload } from "./shared";

export function useProfilesQuery() {
  return useQuery({
    queryKey: adminQueryKeys.profiles,
    queryFn: () => apiGet<ProfilesResponse>("/admin/profiles"),
    select: (response) => response.profiles,
  });
}

export function useProfileMutations() {
  const queryClient = useQueryClient();

  function syncDraft(draft: DraftState) {
    queryClient.setQueryData(adminQueryKeys.draft, draft);
  }

  return {
    saveProfile: useMutation({
      mutationKey: adminMutationKeys.profiles,
      mutationFn: ({ profileId, profile }: { profileId: string; profile: Profile }) =>
        apiJson<DraftState>(`/admin/profiles/${profileId}`, "PUT", buildProfilePayload(profile)),
      onSuccess: syncDraft,
    }),
    createProfile: useMutation({
      mutationKey: adminMutationKeys.profiles,
      mutationFn: (profile: Profile) =>
        apiJson<DraftState>("/admin/profiles", "POST", buildProfilePayload(profile)),
      onSuccess: syncDraft,
    }),
    deleteProfile: useMutation({
      mutationKey: adminMutationKeys.profiles,
      mutationFn: (profileId: string) => apiJson<DraftState>(`/admin/profiles/${profileId}`, "DELETE"),
      onSuccess: syncDraft,
    }),
  };
}
