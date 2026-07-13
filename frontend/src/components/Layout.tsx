import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function Layout() {
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-sky-50 text-slate-900">
      <header className="flex flex-wrap items-center gap-4 border-b border-sky-200 bg-white px-4 py-4 sm:px-6 lg:px-8">
        <NavLink to="/" className="text-lg font-bold text-sky-950 hover:text-sky-700">
          fincode サブスク
        </NavLink>
        {user && (
          <nav className="flex flex-1 items-center gap-4 text-sm font-semibold">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                isActive
                  ? "border-b-2 border-sky-500 px-1 py-2 text-sky-700"
                  : "border-b-2 border-transparent px-1 py-2 text-slate-600 hover:border-sky-200 hover:text-sky-700"
              }
            >
              ホーム
            </NavLink>
            <NavLink
              to="/account"
              className={({ isActive }) =>
                isActive
                  ? "border-b-2 border-sky-500 px-1 py-2 text-sky-700"
                  : "border-b-2 border-transparent px-1 py-2 text-slate-600 hover:border-sky-200 hover:text-sky-700"
              }
            >
              アカウント
            </NavLink>
          </nav>
        )}
        <div className="ml-auto flex items-center gap-4">
          {user ? (
            <span className="text-sm font-medium text-slate-600">{user.name}</span>
          ) : (
            <NavLink
              to="/login"
              className="inline-flex min-h-11 items-center justify-center border border-sky-600 bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
            >
              ログイン
            </NavLink>
          )}
        </div>
      </header>
      <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
        <Outlet />
      </main>
    </div>
  );
}
