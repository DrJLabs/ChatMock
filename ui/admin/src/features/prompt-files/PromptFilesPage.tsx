import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  SurfaceCard,
  SurfaceCardContent,
  SurfaceCardHeader,
  SurfaceCardTitle,
} from "@/components/shared/SurfaceCard";

import type { Profile, PromptFilePayload, PromptState } from "../../lib/types/admin";

type PromptFilesPageProps = {
  profiles: Profile[];
  prompts: PromptState | null;
  busy: boolean;
  onLoadPromptFiles: (payload: {
    base_prompt_path: string;
    codex_prompt_path: string;
  }) => Promise<PromptFilePayload>;
  onSavePromptFiles: (payload: PromptFilePayload) => Promise<PromptFilePayload>;
};

export function PromptFilesPage({
  profiles,
  prompts,
  busy,
  onLoadPromptFiles,
  onSavePromptFiles,
}: PromptFilesPageProps) {
  const [selectedProfileId, setSelectedProfileId] = useState<string>(profiles[0]?.id ?? "");
  const [promptFiles, setPromptFiles] = useState<PromptFilePayload | null>(null);

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0] ?? null,
    [profiles, selectedProfileId],
  );

  useEffect(() => {
    if (selectedProfile == null) {
      setPromptFiles(null);
      return;
    }
    let active = true;
    void (async () => {
      try {
        const payload = await onLoadPromptFiles({
          base_prompt_path: selectedProfile.base_prompt_path,
          codex_prompt_path: selectedProfile.codex_prompt_path,
        });
        if (active) {
          setPromptFiles(payload);
        }
      } catch {
        if (active) {
          setPromptFiles(null);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [onLoadPromptFiles, selectedProfile]);

  if (selectedProfile == null) {
    return (
      <SurfaceCard>
        <SurfaceCardHeader>
          <SurfaceCardTitle>Prompt Files</SurfaceCardTitle>
        </SurfaceCardHeader>
        <SurfaceCardContent className="pt-0">
          <p className="muted">No current profiles are available to map prompt files.</p>
        </SurfaceCardContent>
      </SurfaceCard>
    );
  }

  return (
    <section className="page-grid">
      <div className="mode-header-card">
        <div>
          <p className="eyebrow">Prompt Files</p>
          <h2>Edit the actual prompt text that is used on disk.</h2>
          <p className="muted">These saves are immediate file writes. They do not use the draft/apply workflow.</p>
        </div>
        <div className="prompt-files-actions">
          <label className="picker-field">
            <span>Profile</span>
            <Select onValueChange={setSelectedProfileId} value={selectedProfile.id}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a profile" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {profiles.map((profile) => (
                    <SelectItem key={profile.id} value={profile.id}>
                      {profile.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </label>
          <Button
            disabled={busy}
            variant="outline"
            onClick={async () => {
              try {
                const payload = await onLoadPromptFiles({
                  base_prompt_path: selectedProfile.base_prompt_path,
                  codex_prompt_path: selectedProfile.codex_prompt_path,
                });
                setPromptFiles(payload);
              } catch {
                // App-level error state already reports the failure.
              }
            }}
          >
            Reload From Disk
          </Button>
          <Button
            disabled={busy || promptFiles == null}
            onClick={async () => {
              if (!promptFiles) {
                return;
              }
              try {
                const payload = await onSavePromptFiles(promptFiles);
                setPromptFiles(payload);
              } catch {
                // App-level error state already reports the failure.
              }
            }}
          >
            Save Prompt Files
          </Button>
        </div>
      </div>

      <div className="panel-grid">
        <SurfaceCard>
          <SurfaceCardHeader>
            <SurfaceCardTitle>Current Runtime Prompt Set</SurfaceCardTitle>
          </SurfaceCardHeader>
          <SurfaceCardContent>
            <dl className="key-value-list">
              <div>
                <dt>Active prompt dir</dt>
                <dd>{prompts?.prompt_dir ?? "Unknown"}</dd>
              </div>
              <div>
                <dt>Selected base path</dt>
                <dd>{selectedProfile.base_prompt_path}</dd>
              </div>
              <div>
                <dt>Selected codex path</dt>
                <dd>{selectedProfile.codex_prompt_path}</dd>
              </div>
            </dl>
          </SurfaceCardContent>
        </SurfaceCard>

        <SurfaceCard>
          <SurfaceCardHeader>
            <SurfaceCardTitle>Save Behavior</SurfaceCardTitle>
          </SurfaceCardHeader>
          <SurfaceCardContent>
            <ol className="ordered-list">
              <li>Saving writes the selected prompt files on disk immediately.</li>
              <li>If those files are the active runtime prompt set, the backend reloads them at once.</li>
              <li>Structural profile and instance edits still require Apply Draft on Current State.</li>
            </ol>
          </SurfaceCardContent>
        </SurfaceCard>
      </div>

      {promptFiles == null ? (
        <SurfaceCard>
          <SurfaceCardContent className="pt-5">
            <p className="muted">Loading prompt file contents...</p>
          </SurfaceCardContent>
        </SurfaceCard>
      ) : (
        <section className="prompt-editor-layout">
          <SurfaceCard>
            <SurfaceCardHeader>
              <div>
                <p className="eyebrow">Base Prompt</p>
                <SurfaceCardTitle>{selectedProfile.base_prompt_path}</SurfaceCardTitle>
              </div>
            </SurfaceCardHeader>
            <SurfaceCardContent>
              <Textarea
                className="prompt-textarea"
                rows={18}
                value={promptFiles.base_prompt_text}
                onChange={(event) =>
                  setPromptFiles((current) =>
                    current ? { ...current, base_prompt_text: event.target.value } : current,
                  )
                }
              />
            </SurfaceCardContent>
          </SurfaceCard>

          <SurfaceCard>
            <SurfaceCardHeader>
              <div>
                <p className="eyebrow">Codex Prompt</p>
                <SurfaceCardTitle>{selectedProfile.codex_prompt_path}</SurfaceCardTitle>
              </div>
            </SurfaceCardHeader>
            <SurfaceCardContent>
              <Textarea
                className="prompt-textarea"
                rows={18}
                value={promptFiles.codex_prompt_text}
                onChange={(event) =>
                  setPromptFiles((current) =>
                    current ? { ...current, codex_prompt_text: event.target.value } : current,
                  )
                }
              />
            </SurfaceCardContent>
          </SurfaceCard>
        </section>
      )}
    </section>
  );
}
