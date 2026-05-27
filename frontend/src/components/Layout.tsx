import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function Layout() {
  const { user } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          fincode サブスク
        </NavLink>
        {user && (
          <nav className="primary-nav">
            <NavLink to="/" end>
              ホーム
            </NavLink>
            <NavLink to="/account">アカウント</NavLink>
          </nav>
        )}
        <div className="topbar-right">
          {user ? (
            <>
              <span className="user-name">{user.name}</span>
            </>
          ) : (
            <NavLink to="/login" className="primary-link">
              ログイン
            </NavLink>
          )}
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
