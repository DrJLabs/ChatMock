import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  buildNewProfileFormValues,
  formValuesToProfile,
  profileToFormValues,
  type ProfileFormValues,
} from "@/forms/profileForm";
import type { Profile } from "@/lib/types/admin";

type ProfilesPageProps = {
  profiles: Profile[];
  busy: boolean;
  onSaveProfile: (profileId: string, profile: Profile) => Promise<void>;
  onCreateProfile: (profile: Profile) => Promise<void>;
  onDeleteProfile: (profileId: string) => Promise<void>;
};

function FieldError({ message }: { message?: string }) {
  if (!message) {
    return null;
  }

  return <p className="text-sm text-destructive">{message}</p>;
}

export function ProfilesPage({ profiles, busy, onSaveProfile, onCreateProfile, onDeleteProfile }: ProfilesPageProps) {
  const [selectedId, setSelectedId] = useState<string | null>(profiles[0]?.id ?? null);
  const [isCreating, setIsCreating] = useState(false);

  const {
    formState: { errors, isDirty },
    handleSubmit,
    register,
    reset,
    watch,
  } = useForm<ProfileFormValues>({
    defaultValues: profiles[0] ? profileToFormValues(profiles[0]) : buildNewProfileFormValues(profiles),
  });

  useEffect(() => {
    if (isCreating) {
      return;
    }

    if (selectedId == null) {
      const next = profiles[0] ?? null;
      setSelectedId(next?.id ?? null);
      reset(next ? profileToFormValues(next) : buildNewProfileFormValues(profiles));
      return;
    }

    const next = profiles.find((profile) => profile.id === selectedId) ?? profiles[0] ?? null;
    setSelectedId(next?.id ?? null);
    reset(next ? profileToFormValues(next) : buildNewProfileFormValues(profiles));
  }, [isCreating, profiles, reset, selectedId]);

  const currentLabel = watch("label");
  const activeProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedId) ?? profiles[0] ?? null,
    [profiles, selectedId],
  );

  if (!isCreating && activeProfile == null) {
    return (
      <section className="panel-card">
        <h2>Profiles</h2>
        <p className="muted">No draft profiles are loaded yet.</p>
      </section>
    );
  }

  async function onSubmit(values: ProfileFormValues) {
    const profile = formValuesToProfile(values);

    if (isCreating) {
      await onCreateProfile(profile);
      setIsCreating(false);
      setSelectedId(profile.id);
      return;
    }

    await onSaveProfile(profile.id, profile);
  }

  return (
    <section className="editor-layout">
      <aside className="sidebar-card">
        <div className="sidebar-header">
          <div>
            <p className="eyebrow">Draft Profiles</p>
            <h2>Profiles</h2>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setIsCreating(true);
              setSelectedId(null);
              reset(buildNewProfileFormValues(profiles));
            }}
          >
            New Profile
          </Button>
        </div>
        <div className="sidebar-list">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              className={`list-item ${profile.id === selectedId && !isCreating ? "active" : ""}`}
              onClick={() => {
                setIsCreating(false);
                setSelectedId(profile.id);
                reset(profileToFormValues(profile));
              }}
            >
              <strong>{profile.label}</strong>
              <span>{profile.prompt_dir}</span>
            </button>
          ))}
        </div>
      </aside>

      <article className="editor-card">
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="editor-header">
            <div>
              <p className="eyebrow">{isCreating ? "Create" : "Edit"}</p>
              <h3>{isCreating ? "New Profile Draft" : currentLabel || activeProfile?.label || "Profile"}</h3>
            </div>
            <div className="editor-actions">
              {!isCreating && activeProfile ? (
                <Button
                  size="sm"
                  type="button"
                  variant="destructive"
                  onClick={async () => {
                    if (!window.confirm(`Delete profile ${activeProfile.id} from the draft?`)) {
                      return;
                    }
                    await onDeleteProfile(activeProfile.id);
                    setSelectedId(null);
                  }}
                >
                  Delete
                </Button>
              ) : null}
              <Button disabled={busy || (!isCreating && !isDirty)} type="submit">
                {busy ? "Saving..." : isCreating ? "Create Draft Profile" : "Save Draft Profile"}
              </Button>
            </div>
          </div>

          <div className="form-grid">
            <label>
              <span>Profile ID</span>
              <Input
                aria-invalid={errors.id ? true : undefined}
                readOnly={!isCreating}
                {...register("id", {
                  required: "Profile ID is required.",
                })}
              />
              <FieldError message={errors.id?.message} />
            </label>
            <label>
              <span>Label</span>
              <Input
                aria-invalid={errors.label ? true : undefined}
                {...register("label", {
                  required: "Label is required.",
                })}
              />
              <FieldError message={errors.label?.message} />
            </label>
            <label className="full-width">
              <span>Description</span>
              <Textarea rows={3} {...register("description")} />
            </label>
            <label className="full-width">
              <span>Prompt Directory</span>
              <Input
                aria-invalid={errors.prompt_dir ? true : undefined}
                {...register("prompt_dir", {
                  required: "Prompt directory is required.",
                })}
              />
              <FieldError message={errors.prompt_dir?.message} />
            </label>
            <label className="full-width">
              <span>Base Prompt Path</span>
              <Input
                aria-invalid={errors.base_prompt_path ? true : undefined}
                {...register("base_prompt_path", {
                  required: "Base prompt path is required.",
                })}
              />
              <FieldError message={errors.base_prompt_path?.message} />
            </label>
            <label className="full-width">
              <span>Codex Prompt Path</span>
              <Input
                aria-invalid={errors.codex_prompt_path ? true : undefined}
                {...register("codex_prompt_path", {
                  required: "Codex prompt path is required.",
                })}
              />
              <FieldError message={errors.codex_prompt_path?.message} />
            </label>
          </div>

          <details className="advanced-card">
            <summary>Advanced</summary>
            <div className="form-grid advanced-grid">
              <label>
                <span>UI Order</span>
                <Input
                  aria-invalid={errors.ui_order ? true : undefined}
                  type="number"
                  {...register("ui_order", {
                    valueAsNumber: true,
                    min: {
                      value: 0,
                      message: "UI Order must be 0 or greater.",
                    },
                  })}
                />
                <FieldError message={errors.ui_order?.message} />
              </label>
              <label className="checkbox-field">
                <input type="checkbox" {...register("inject_default_instructions")} />
                <span>Inject default instructions</span>
              </label>
              <label className="checkbox-field">
                <input type="checkbox" {...register("editable")} />
                <span>Editable in UI</span>
              </label>
            </div>
          </details>
        </form>
      </article>
    </section>
  );
}
