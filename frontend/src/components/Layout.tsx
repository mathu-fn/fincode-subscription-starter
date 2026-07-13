import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { mutedTextClass, primaryLinkClass } from "../lib/styles";

// ナビリンク: アクティブは黒字 + 黒の下線、非アクティブは muted で下線は透明。
// 色ではなく下線で現在地を示す（赤は使わない）。ラベルは等幅・大文字・レタースペーシング。
const navBase =
  "border-b-2 px-1 py-2 font-mono text-xs uppercase tracking-[0.1em] transition-colors duration-150";
const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? `${navBase} border-black text-black`
    : `${navBase} border-transparent text-muted hover:text-black`;

export function Layout() {
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-white text-black">
      <header className="flex flex-wrap items-center gap-4 border-b border-line bg-white px-4 py-4 sm:px-6 lg:px-8">
        <NavLink
          to="/"
          className="font-dot text-lg tracking-tight text-black transition-colors duration-150 hover:text-muted"
        >
          fincode サブスク
        </NavLink>
        {user && (
          <nav className="flex flex-1 items-center gap-4">
            <NavLink to="/" end className={navLinkClass}>
              ホーム
            </NavLink>
            <NavLink to="/account" className={navLinkClass}>
              アカウント
            </NavLink>
          </nav>
        )}
        <div className="ml-auto flex items-center gap-4">
          {user ? (
            <span className={mutedTextClass}>{user.name}</span>
          ) : (
            <NavLink to="/login" className={primaryLinkClass}>
              ログイン
            </NavLink>
          )}
        </div>
      </header>
      <main className="flex-1 bg-white px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
        <Outlet />
      </main>
    </div>
  );
}
