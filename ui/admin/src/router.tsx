import type { RouteObject } from "react-router";
import { createBrowserRouter } from "react-router";

import App from "./App";
import { AdminLayout } from "./layouts/AdminLayout";
import { CurrentStateRoute } from "./routes/CurrentStateRoute";
import { EditConfigRoute } from "./routes/EditConfigRoute";
import { PromptFilesRoute } from "./routes/PromptFilesRoute";

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
        ],
      },
    ],
  },
];

export const router = createBrowserRouter(adminRoutes, {
  basename: "/admin/ui",
});
