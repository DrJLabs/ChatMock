import { NavLink, Outlet } from "react-router";

import { useAdminApp } from "../App";

const NAV_ITEMS = [
  { to: "/", label: "Current State", end: true },
  { to: "/edit-config", label: "Edit Config" },
  { to: "/prompt-files", label: "Prompt Files" },
];

export function AdminLayout() {
  const { busy, statusText } = useAdminApp();

  return (
    <div className="app-shell">
      <div className="app-frame">
        <header className="topbar">
          <div>
            <p className="eyebrow">ChatMock</p>
            <h1>Browser Admin</h1>
            <p className="muted">Operator-first control surface for runtime status, structural config, and prompt files.</p>
          </div>
          <aside className="status-banner">
            <strong>{busy ? "Working..." : "Status"}</strong>
            <span>{statusText}</span>
          </aside>
        </header>

        <div className="app-body">
          <aside className="nav-card">
            <nav aria-label="Admin pages">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  className={({ isActive }) => `nav-button ${isActive ? "active" : ""}`}
                  end={item.end}
                  to={item.to}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </aside>

          <main className="main-column">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
