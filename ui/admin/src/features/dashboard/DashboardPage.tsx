import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/shared/StatCard";
import {
  SurfaceCard,
  SurfaceCardContent,
  SurfaceCardDescription,
  SurfaceCardHeader,
  SurfaceCardTitle,
} from "@/components/shared/SurfaceCard";

import type {
  DraftPreview,
  DraftState,
  InstancePreview,
  PromptState,
  RuntimeRedeployResponse,
  ValidationSummary,
} from "../../lib/types/admin";

type DashboardPageProps = {
  draft: DraftState | null;
  currentProfileCount: number;
  currentInstanceCount: number;
  runtimeValidation: ValidationSummary | null;
  prompts: PromptState | null;
  previews: InstancePreview[];
  draftValidation: ValidationSummary | null;
  draftPreview: DraftPreview | null;
  busy: boolean;
  onNavigate: (page: string) => void;
  onReloadPrompts: () => Promise<void>;
  onValidateRuntime: () => Promise<void>;
  onApplyDraft: () => Promise<void>;
  onRedeploy: () => Promise<RuntimeRedeployResponse | void>;
  onValidateDraft: () => Promise<void>;
  onPreviewDraft: () => Promise<void>;
  onResetDraft: () => Promise<void>;
};

export function DashboardPage({
  draft,
  currentProfileCount,
  currentInstanceCount,
  runtimeValidation,
  prompts,
  previews,
  draftValidation,
  draftPreview,
  busy,
  onNavigate,
  onReloadPrompts,
  onValidateRuntime,
  onApplyDraft,
  onRedeploy,
  onValidateDraft,
  onPreviewDraft,
  onResetDraft,
}: DashboardPageProps) {
  return (
    <section className="page-grid">
      <div className="current-state-hero">
        <div>
          <p className="eyebrow">Current State</p>
          <h2>See what is live first, then act deliberately.</h2>
          <p className="muted">
            Runtime actions are immediate. Structural profile and instance changes stay in the draft until you apply them.
          </p>
        </div>
        <div className="current-state-actions">
          <Button disabled={busy} variant="outline" onClick={onReloadPrompts}>
            Reload Prompts
          </Button>
          <Button disabled={busy} variant="outline" onClick={onValidateRuntime}>
            Validate Runtime
          </Button>
          {draft?.dirty ? (
            <Button disabled={busy} variant="secondary" onClick={onApplyDraft}>
              Apply Draft
            </Button>
          ) : null}
          <Button
            disabled={busy}
            variant="destructive"
            onClick={async () => {
              if (!window.confirm("Redeploy the running ChatMock stack now?")) {
                return;
              }
              await onRedeploy();
            }}
          >
            Redeploy
          </Button>
        </div>
      </div>

      <div className="current-state-grid">
        <StatCard
          action={
            <Button className="justify-start px-0" size="sm" variant="link" onClick={() => onNavigate("edit-config")}>
              Edit config
            </Button>
          }
          label="Profiles"
          value={currentProfileCount}
        />
        <StatCard
          action={
            <Button className="justify-start px-0" size="sm" variant="link" onClick={() => onNavigate("edit-config")}>
              Review services
            </Button>
          }
          label="Instances"
          value={currentInstanceCount}
        />
        <StatCard
          label="Runtime Validation"
          note={runtimeValidation?.ok ? "Registries validated cleanly." : runtimeValidation?.errors[0] ?? "Not run yet."}
          value={runtimeValidation?.ok ? "Healthy" : "Needs attention"}
        />
        <StatCard
          action={
            <Button className="justify-start px-0" size="sm" variant="link" onClick={() => onNavigate("prompt-files")}>
              Edit prompt files
            </Button>
          }
          label="Prompt Source"
          value={prompts?.prompt_dir ?? "Unknown"}
        />
      </div>

      <div className="panel-grid">
        <SurfaceCard>
          <SurfaceCardHeader>
            <SurfaceCardTitle>Current Services</SurfaceCardTitle>
          </SurfaceCardHeader>
          <SurfaceCardContent>
            <dl className="key-value-list">
              {previews.map((preview) => (
                <div key={preview.instance.id}>
                  <dt>{preview.instance.label}</dt>
                  <dd>
                    {preview.instance.bind_host}:{preview.instance.port}
                  </dd>
                </div>
              ))}
            </dl>
          </SurfaceCardContent>
        </SurfaceCard>

        <SurfaceCard>
          <SurfaceCardHeader>
            <SurfaceCardTitle>Draft State</SurfaceCardTitle>
            <SurfaceCardDescription>Structural changes remain in-memory until you apply them.</SurfaceCardDescription>
          </SurfaceCardHeader>
          <SurfaceCardContent>
            <dl className="key-value-list">
              <div>
                <dt>Dirty</dt>
                <dd>{draft?.dirty ? "Yes" : "No"}</dd>
              </div>
              <div>
                <dt>Profiles in draft</dt>
                <dd>{draft?.profiles.length ?? 0}</dd>
              </div>
              <div>
                <dt>Instances in draft</dt>
                <dd>{draft?.instances.length ?? 0}</dd>
              </div>
              <div>
                <dt>Draft validation</dt>
                <dd>{draftValidation?.ok ? "Passing" : draft?.dirty ? "Not reviewed" : "Clean"}</dd>
              </div>
            </dl>
            {draft?.dirty ? (
              <div className="draft-actions">
                <Button disabled={busy} variant="outline" onClick={onValidateDraft}>
                  Validate Draft
                </Button>
                <Button disabled={busy} variant="outline" onClick={onPreviewDraft}>
                  Preview Draft
                </Button>
                <Button disabled={busy} variant="destructive" onClick={onResetDraft}>
                  Discard Draft
                </Button>
              </div>
            ) : null}
          </SurfaceCardContent>
        </SurfaceCard>
      </div>

      {draft?.dirty ? (
        <div className="panel-grid">
          <SurfaceCard>
            <SurfaceCardHeader>
              <SurfaceCardTitle>Pending Changes</SurfaceCardTitle>
            </SurfaceCardHeader>
            <SurfaceCardContent>
              {draftPreview == null ? (
                <p className="muted">Preview the draft to see updated bind targets and profile wiring before you apply it.</p>
              ) : (
                <div className="stack">
                  {Object.entries(draftPreview.compose_preview.services).map(([serviceName, service]) => (
                    <div key={serviceName} className="preview-card">
                      <strong>{serviceName}</strong>
                      <span>{service.bind}</span>
                      <span className="muted">Profile: {service.profile_id}</span>
                    </div>
                  ))}
                </div>
              )}
            </SurfaceCardContent>
          </SurfaceCard>

          <SurfaceCard>
            <SurfaceCardHeader>
              <SurfaceCardTitle>Working Rules</SurfaceCardTitle>
            </SurfaceCardHeader>
            <SurfaceCardContent>
              <ol className="ordered-list">
                <li>Edit structural profile and instance config in Edit Config.</li>
                <li>Edit actual prompt text in Prompt Files.</li>
                <li>Apply Draft only when structural changes are ready to persist.</li>
              </ol>
            </SurfaceCardContent>
          </SurfaceCard>
        </div>
      ) : null}
    </section>
  );
}
