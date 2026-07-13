// ローディング中のレイアウトシフトを抑えるためのプレースホルダーバー。
// 装飾要素なので aria-hidden="true" を付け、スクリーンリーダーや getByRole("status")
// には拾わせない（読み込み状態は周囲のテキストやライブリージョンで伝える）。

type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={`block bg-sky-100${className ? ` ${className}` : ""}`}
    />
  );
}
