import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "./lib/query-client";
import { UISettingsProvider } from "./lib/settings/provider";
import { adminRoutes } from "./router";

describe("admin router", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockImplementation(async (input) => {
      const path = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;

      if (path === "/admin/profiles") {
        return Response.json({ profiles: [] });
      }

      if (path === "/admin/instances") {
        return Response.json({ instances: [] });
      }

      if (path === "/admin/prompts") {
        return Response.json({
          prompt_dir: "prompts/bare",
          base_prompt_path: "prompts/bare/prompt.md",
          codex_prompt_path: "prompts/bare/prompt_gpt5_codex.md",
          base_prompt_text: "",
          codex_prompt_text: "",
        });
      }

      if (path === "/admin/runtime/validate") {
        return Response.json({
          ok: true,
          errors: [],
          profiles: [],
          instances: [],
        });
      }

      if (path === "/admin/draft") {
        return Response.json({
          profiles: [],
          instances: [],
          dirty: false,
          last_loaded_at: Date.now(),
        });
      }

      throw new Error(`Unhandled test fetch: ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the edit config screen from pathname routing and exposes nav links", async () => {
    const router = createMemoryRouter(adminRoutes, {
      initialEntries: ["/edit-config"],
    });
    const queryClient = createQueryClient();

    render(
      <UISettingsProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </UISettingsProvider>,
    );

    expect(
      await screen.findByText("Make structural YAML-backed changes without touching the live runtime yet."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Edit Config" })).toHaveAttribute("href", "/edit-config");
  });

  it("renders the settings screen from pathname routing and exposes nav links", async () => {
    const router = createMemoryRouter(adminRoutes, {
      basename: "/admin/ui",
      initialEntries: ["/admin/ui/settings"],
    });
    const queryClient = createQueryClient();

    render(
      <UISettingsProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </UISettingsProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "Browser-local settings", level: 2 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Settings", current: "page" })).toHaveAttribute("href", "/admin/ui/settings");
    expect(screen.getByRole("tab", { name: "UI" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Behavior" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "About" })).toBeInTheDocument();
    expect(screen.getByText("Theme")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Midnight" })).toBeInTheDocument();
    expect(screen.getByLabelText("Code and prompt text size")).toBeInTheDocument();
  });

  it("resets unapplied settings preview when leaving the settings route", async () => {
    const router = createMemoryRouter(adminRoutes, {
      basename: "/admin/ui",
      initialEntries: ["/admin/ui/settings"],
    });
    const queryClient = createQueryClient();

    render(
      <UISettingsProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </UISettingsProvider>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Midnight" }));
    fireEvent.change(screen.getByLabelText("Code and prompt text size"), {
      target: { value: "120" },
    });

    expect(document.documentElement.dataset.theme).toBe("midnight");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");

    fireEvent.click(screen.getByRole("link", { name: "Current State" }));

    expect(await screen.findByText("See what is live first, then act deliberately.")).toBeInTheDocument();
    expect(document.documentElement.dataset.theme).toBe("obsidian");
    expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("100");
  });

  it("keeps applied settings active when applying without leaving the route", async () => {
    const router = createMemoryRouter(adminRoutes, {
      basename: "/admin/ui",
      initialEntries: ["/admin/ui/settings"],
    });
    const queryClient = createQueryClient();

    render(
      <UISettingsProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </UISettingsProvider>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Midnight" }));
    fireEvent.change(screen.getByLabelText("Code and prompt text size"), {
      target: { value: "120" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    await waitFor(() => {
      expect(screen.getByText("Applied settings are active.")).toBeInTheDocument();
      expect(document.documentElement.dataset.theme).toBe("midnight");
      expect(document.documentElement.style.getPropertyValue("--admin-code-scale")).toBe("120");
      expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
    });
  });
});
