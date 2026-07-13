// ルートガード（認証確認中など）で使う、ページ全幅のローディング表示。
// App の RootRoute と RequireAuth で共有する。
export function PageLoading() {
  return <div className="mx-auto grid max-w-5xl gap-6 text-muted">読み込み中...</div>;
}
