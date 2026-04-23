import type { InstancePreview, PromptState, RuntimeRedeployResponse, ValidationSummary } from "../../lib/types/admin";

type RuntimeActionsPageProps = {
  prompts: PromptState | null;
  validation: ValidationSummary | null;
  previews: InstancePreview[];
  busy: boolean;
  onValidate: () => Promise<void>;
  onReloadPrompts: () => Promise<void>;
  onRedeploy: () => Promise<RuntimeRedeployResponse | void>;
};

export function RuntimeActionsPage({
  prompts,
  validation,
  previews,
  busy,
  onValidate,
  onReloadPrompts,
  onRedeploy,
}: RuntimeActionsPageProps) {
  return (
    <section className="page-grid">
      <div className="panel-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Runtime Controls</p>
            <h2>Immediate operator actions stay separate from draft config edits.</h2>
          </div>
          <div className="editor-actions">
            <button className="secondary-button" disabled={busy} onClick={onValidate}>
              Validate Current Runtime
            </button>
            <button className="secondary-button" disabled={busy} onClick={onReloadPrompts}>
              Reload Prompts
            </button>
            <button
              className="danger-button"
              disabled={busy}
              onClick={async () => {
                if (!window.confirm("Redeploy the running ChatMock stack now?")) {
                  return;
                }
                await onRedeploy();
              }}
            >
              Redeploy
            </button>
          </div>
        </div>
        <dl className="key-value-list">
          <div>
            <dt>Validation</dt>
            <dd>{validation?.ok ? "Passing" : "Not validated"}</dd>
          </div>
          <div>
            <dt>Prompt dir</dt>
            <dd>{prompts?.prompt_dir ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Base prompt</dt>
            <dd>{prompts?.base_prompt_path ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Codex prompt</dt>
            <dd>{prompts?.codex_prompt_path ?? "Unknown"}</dd>
          </div>
        </dl>
      </div>

      <article className="panel-card">
        <h3>Current Instance Preview</h3>
        <div className="preview-grid">
          {previews.map((preview) => (
            <div key={preview.instance.id} className="preview-card">
              <strong>{preview.instance.label}</strong>
              <span>
                {preview.instance.bind_host}:{preview.instance.port}
              </span>
              <span className="muted">Service: {preview.instance.compose_service_name}</span>
              <code>{preview.runtime.volumes.join(" · ")}</code>
            </div>
          ))}
        </div>
      </article>

      <article className="panel-card">
        <h3>Validation Errors</h3>
        {validation?.errors.length ? (
          <ul className="error-list">
            {validation.errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">No runtime validation errors reported.</p>
        )}
      </article>
    </section>
  );
}
