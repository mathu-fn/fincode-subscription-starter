/**
 * fincode モックモードの判定。
 *
 * `VITE_FINCODE_MODE=mock` のとき、フロントエンドは fincode.js を読み込まず、
 * カード登録フォームはテストトークンを直接入力する簡易フォームに切り替わる。
 * これにより fincode の公開鍵やアカウントが無くても UI を一通り操作できる。
 * バックエンドの `FINCODE_MODE=mock` と対になる設定。
 */
export function isFincodeMockMode(): boolean {
  return String(import.meta.env.VITE_FINCODE_MODE ?? "").toLowerCase() === "mock";
}
