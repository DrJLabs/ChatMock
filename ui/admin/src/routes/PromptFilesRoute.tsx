import { useAdminApp } from "../App";
import { PromptFilesPage } from "../features/prompt-files/PromptFilesPage";

export function PromptFilesRoute() {
  const { profiles, prompts, busy, loadPromptFiles, savePromptFiles } = useAdminApp();

  return (
    <PromptFilesPage
      profiles={profiles}
      prompts={prompts}
      busy={busy}
      onLoadPromptFiles={loadPromptFiles}
      onSavePromptFiles={savePromptFiles}
    />
  );
}
