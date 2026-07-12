/**
 * HomePage 系テストで共有する apiFetch モックのルーティングテーブル。
 *
 * vi.mock はトップレベルで hoist される必要があるため、`vi.mock(...)` 呼び出し
 * 自体は各テストファイルに残し、ここではモック実装（ルーティング）だけを共有する。
 */

/** ルート値。固定値、または (path, init) を受けて値を返す関数。 */
export type ApiRouteValue = unknown | ((path: string, init?: RequestInit) => unknown);

export type ApiRoutes = Record<string, ApiRouteValue>;

export const emptyHistoryPage = { data: [], page: 1, per_page: 10, total: 0 };

const defaultRoutes: ApiRoutes = {
  "/api/subscription": null,
  "/api/subscription/plans": [],
  "/api/subscription/cards": [],
  "/api/subscription/history": emptyHistoryPage
};

/**
 * apiFetch の mockImplementation に渡す実装を生成する。
 *
 * - まずパス完全一致、次にクエリ文字列を除いたパスでルートを引く
 * - どちらにも無ければ null を返す（従来のフォールバックと同じ）
 * - overrides はデフォルトルートをキー単位で上書きする
 */
export function mockApiFetch(overrides: ApiRoutes = {}) {
  const routes: ApiRoutes = { ...defaultRoutes, ...overrides };
  return (path: string, init?: RequestInit): Promise<unknown> => {
    const key = path in routes ? path : path.split("?")[0];
    const value = key in routes ? routes[key] : null;
    const resolved = typeof value === "function" ? (value as (p: string, i?: RequestInit) => unknown)(path, init) : value;
    return Promise.resolve(resolved);
  };
}
