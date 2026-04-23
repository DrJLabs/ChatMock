import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";

import { PromptFilesPage } from "./PromptFilesPage";
import type { Profile, PromptFilePayload, PromptState } from "../../lib/types/admin";

const PROFILE: Profile = {
  id: "bare",
  label: "Bare",
  description: "Default profile",
  prompt_dir: "chatmock/bundled_prompts/bare",
  base_prompt_path: "chatmock/bundled_prompts/bare/prompt.md",
  codex_prompt_path: "chatmock/bundled_prompts/bare/prompt_gpt5_codex.md",
  runtime_defaults: { inject_default_instructions: true },
  ui: { order: 10, editable: true },
};

const PROMPT_STATE: PromptState = {
  prompt_dir: "chatmock/bundled_prompts/bare",
  base_prompt_path: "chatmock/bundled_prompts/bare/prompt.md",
  codex_prompt_path: "chatmock/bundled_prompts/bare/prompt_gpt5_codex.md",
  base_prompt_text: "base",
  codex_prompt_text: "codex",
  prompt_config_path: "/data/prompt-config.json",
};

const PROMPT_FILES: PromptFilePayload = {
  base_prompt_path: "chatmock/bundled_prompts/bare/prompt.md",
  codex_prompt_path: "chatmock/bundled_prompts/bare/prompt_gpt5_codex.md",
  base_prompt_text: "base",
  codex_prompt_text: "codex",
  reloaded_current_prompt_set: false,
};

function PromptFilesHarness({
  onLoad,
}: {
  onLoad: (payload: {
    base_prompt_path: string;
    codex_prompt_path: string;
  }) => Promise<PromptFilePayload>;
}) {
  const [, setVersion] = useState(0);

  const onLoadPromptFiles = async (payload: {
    base_prompt_path: string;
    codex_prompt_path: string;
  }) => {
    const result = await onLoad(payload);
    setVersion((current) => current + 1);
    return result;
  };

  return (
    <PromptFilesPage
      profiles={[PROFILE]}
      prompts={PROMPT_STATE}
      busy={false}
      onLoadPromptFiles={onLoadPromptFiles}
      onSavePromptFiles={vi.fn(async () => PROMPT_FILES)}
    />
  );
}

describe("PromptFilesPage", () => {
  it("loads prompt files once even if the parent rerenders after load", async () => {
    const onLoad = vi.fn(async () => PROMPT_FILES);

    render(<PromptFilesHarness onLoad={onLoad} />);

    await screen.findByDisplayValue("base");

    await waitFor(() => {
      expect(onLoad).toHaveBeenCalledTimes(1);
    });
  });
});
