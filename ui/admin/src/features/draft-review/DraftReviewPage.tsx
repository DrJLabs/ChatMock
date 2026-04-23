import type { DraftPreview, DraftState, ValidationSummary } from "../../lib/types/admin";

type DraftReviewPageProps = {
  draft: DraftState | null;
  validation: ValidationSummary | null;
  preview: DraftPreview | null;
  busy: boolean;
  onValidate: () => Promise<void>;
  onPreview: () => Promise<void>;
  onApply: () => Promise<void>;
  onReset: () => Promise<void>;
};

export function DraftReviewPage({
  draft,
  validation,
  preview,
  busy,
  onValidate,
  onPreview,
  onApply,
  onReset,
}: DraftReviewPageProps) {
  const canApply = Boolean(draft?.dirty && validation?.ok);

  return (
    <section className="page-grid">
      <div className="panel-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Draft Review</p>
            <h2>Validate, preview, and decide when YAML should change.</h2>
          </div>
          <div className="editor-actions">
            <button className="secondary-button" disabled={busy} onClick={onValidate}>
              Validate Draft
            </button>
            <button className="secondary-button" disabled={busy} onClick={onPreview}>
              Refresh Preview
            </button>
            <button className="danger-button" disabled={busy} onClick={onReset}>
              Discard Draft
            </button>
            <button className="primary-button" disabled={busy || !canApply} onClick={onApply}>
              Apply Draft
            </button>
          </div>
        </div>
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
            <dt>Validation</dt>
            <dd>{validation == null ? "Not run" : validation.ok ? "Passing" : "Needs attention"}</dd>
          </div>
        </dl>
      </div>

      <div className="panel-grid">
        <article className="panel-card">
          <h3>Validation Summary</h3>
          {validation == null ? (
            <p className="muted">Run validation to confirm the draft is structurally sound.</p>
          ) : validation.ok ? (
            <p className="success-note">The draft validates cleanly against the current registry rules.</p>
          ) : (
            <ul className="error-list">
              {validation.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          )}
        </article>

        <article className="panel-card">
          <h3>Compose Preview</h3>
          {preview == null ? (
            <p className="muted">Preview the draft to see generated bind targets and service grouping.</p>
          ) : (
            <div className="stack">
              {Object.entries(preview.compose_preview.services).map(([serviceName, service]) => (
                <div key={serviceName} className="preview-card">
                  <strong>{serviceName}</strong>
                  <span>{service.bind}</span>
                  <span className="muted">Profile: {service.profile_id}</span>
                </div>
              ))}
            </div>
          )}
        </article>
      </div>

      <article className="panel-card">
        <h3>Instance Preview</h3>
        {preview == null ? (
          <p className="muted">Run preview to inspect per-instance environment wiring.</p>
        ) : (
          <div className="preview-grid">
            {preview.instance_previews.map((instancePreview) => (
              <div key={instancePreview.instance.id} className="preview-card">
                <strong>{instancePreview.instance.label}</strong>
                <span>
                  {instancePreview.instance.bind_host}:{instancePreview.instance.port}
                </span>
                <span className="muted">Prompt dir: {instancePreview.profile.prompt_dir}</span>
                <code>{Object.keys(instancePreview.runtime.environment).join(" · ")}</code>
              </div>
            ))}
          </div>
        )}
      </article>
    </section>
  );
}
