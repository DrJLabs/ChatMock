import type { RouteObject } from "react-router";
import { createBrowserRouter } from "react-router";

import App from "./App";
import { AdminLayout } from "./layouts/AdminLayout";
import { CurrentStateRoute } from "./routes/CurrentStateRoute";
import { EditConfigRoute } from "./routes/EditConfigRoute";
import { PromptFilesRoute } from "./routes/PromptFilesRoute";
import { SettingsRoute } from "./routes/SettingsRoute";

export const adminRoutes: RouteObject[] = [
  {
    path: "/",
    element: <App />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          {
            index: true,
            element: <CurrentStateRoute />,
          },
          {
            path: "edit-config",
            element: <EditConfigRoute />,
          },
          {
            path: "prompt-files",
            element: <PromptFilesRoute />,
          },
          {
            path: "settings",
            element: <SettingsRoute />,
          },
        ],
      },
    ],
  },
];

export const router = createBrowserRouter(adminRoutes, {
  basename: "/admin/ui",
});
