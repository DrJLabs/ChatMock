import { Button } from "@/components/ui/button";
import {
  SurfaceCard,
  SurfaceCardContent,
  SurfaceCardDescription,
  SurfaceCardHeader,
  SurfaceCardTitle,
} from "@/components/shared/SurfaceCard";

import { useUISettings } from "../../lib/settings/provider";
import { THEME_PRESETS } from "../../lib/settings/theme-presets";
import { CODE_SCALE_STEP, MAX_CODE_SCALE, MIN_CODE_SCALE } from "../../lib/settings/types";

export function UISettingsSection() {
  const {
    appliedSettings,
    draftSettings,
    isDirty,
    setDraftThemeId,
    setDraftCodeScale,
    applyUISettingsDraft,
    resetUISettingsDraft,
  } = useUISettings();

  return (
    <section className="page-grid">
      <div className="panel-grid">
        <SurfaceCard>
          <SurfaceCardHeader>
            <SurfaceCardTitle>Theme</SurfaceCardTitle>
            <SurfaceCardDescription>Dark-first presets preview immediately in this browser.</SurfaceCardDescription>
          </SurfaceCardHeader>
          <SurfaceCardContent className="stack">
            {THEME_PRESETS.map((preset) => {
              const isActive = draftSettings.themeId === preset.id;
              const isApplied = appliedSettings.themeId === preset.id;

              return (
                <button
                  key={preset.id}
                  className={`theme-preset-card ${isActive ? "active" : ""} ${preset.previewClassName}`}
                  aria-label={preset.label}
                  aria-pressed={isActive}
                  data-active={isActive}
                  data-applied={isApplied}
                  onClick={() => setDraftThemeId(preset.id)}
                  type="button"
                >
                  <strong>{preset.label}</strong>
                  <span>{preset.description}</span>
                  {isApplied ? <em>Applied</em> : null}
                </button>
              );
            })}
          </SurfaceCardContent>
        </SurfaceCard>

        <SurfaceCard>
          <SurfaceCardHeader>
            <SurfaceCardTitle>Code And Prompt Text Size</SurfaceCardTitle>
            <SurfaceCardDescription>Adjust technical-text readability without rescaling the whole shell.</SurfaceCardDescription>
          </SurfaceCardHeader>
          <SurfaceCardContent className="stack">
            <label className="picker-field">
              <span>Code and prompt text size</span>
              <input
                aria-label="Code and prompt text size"
                max={MAX_CODE_SCALE}
                min={MIN_CODE_SCALE}
                onChange={(event) => setDraftCodeScale(Number(event.target.value))}
                step={CODE_SCALE_STEP}
                type="range"
                value={draftSettings.codeScale}
              />
              <span>{draftSettings.codeScale}%</span>
            </label>
          </SurfaceCardContent>
        </SurfaceCard>
      </div>

      <SurfaceCard>
        <SurfaceCardHeader>
          <SurfaceCardTitle>Preview State</SurfaceCardTitle>
        </SurfaceCardHeader>
        <SurfaceCardContent className="draft-actions">
          <p className="muted">{isDirty ? "Previewing changes" : "Applied settings are active."}</p>
          <Button disabled={!isDirty} onClick={applyUISettingsDraft} type="button">
            Apply
          </Button>
          <Button disabled={!isDirty} onClick={resetUISettingsDraft} type="button" variant="outline">
            Reset
          </Button>
        </SurfaceCardContent>
      </SurfaceCard>
    </section>
  );
}
