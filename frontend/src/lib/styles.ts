// ==========================================================================
// Nothing 風デザインシステム — 共有クラス文字列（利用契約 / usage contract）
// ==========================================================================
// 複数ページで共有する Tailwind クラス文字列をここに集約する。並列で UI を触る
// 際も、ここと共通プリミティブ（components/Label, StatusDot, Card, SpecTable,
// FormField）を必ず経由し、各ファイルで独自の配色・markup を発明しない。
//
// 原則（DESIGN.md 準拠）:
//   - 背景は白（bg-white）か黒（bg-black）のみ。中途半端な色を作らない。
//   - 色は信号。赤（text-accent / bg-accent）は 1 画面 1〜2 箇所まで、面で塗らない。
//   - 見出し = font-dot、本文 = font-sans（既定）、ラベル/数値 = font-mono。
//   - ドット系フォント（font-dot）は本文に使わない。
//   - 罫線は 1px の薄グレー（border-line）。影・グラデーション禁止。
//   - 余白は多め。遷移は 150〜250ms のスナップ（duration-150 / duration-200）。
//
// 語彙（どれを使うか）:
//   ボタン（主）      … primaryBtn / primaryLinkClass（黒塗り・ホバーで反転）
//   ボタン（副）      … secondaryBtn（枠線のみ）
//   ラベル/キャプション… labelClass（等幅・大文字・レタースペーシング）
//   入力              … inputClass（FormField/Input プリミティブが内包）
//   カード            … <Card>（components/Card）。padding は className でページ毎に付与
//   見出し            … sectionTitle（font-dot）
//   小バッジ          … badgeClass（モノクロ。ステータスは StatusBadge を使う）
//   罫線テーブル      … specTableClass / specRowClass（SpecTable が内包）
//   副次テキスト      … mutedTextClass
// ==========================================================================

// --- ボタン / リンク（主 = 黒塗り、ホバーで白黒反転） -----------------------
const primaryBase =
  "inline-flex min-h-11 items-center justify-center border border-black bg-black font-mono text-xs uppercase tracking-[0.1em] text-white transition-colors duration-150 hover:bg-white hover:text-black focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2";
export const primaryLinkClass = `${primaryBase} px-5 py-2.5`;
export const primaryBtn = `${primaryBase} px-6 py-3`;
export const secondaryBtn =
  "inline-flex min-h-11 items-center justify-center border border-black bg-white px-6 py-3 font-mono text-xs uppercase tracking-[0.1em] text-black transition-colors duration-150 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2";

// --- レイアウト（HomePage 等の外枠） ---------------------------------------
export const pageClass = "mx-auto grid max-w-5xl gap-8";
export const sectionClass = "grid scroll-mt-24 gap-4";

// --- フォーム入力 ----------------------------------------------------------
// labelClass はキャプション「文字」のスタイル（等幅+大文字+レタースペーシング、
// DESIGN の .label に相当）。入力要素へ text-transform/letter-spacing が継承漏れ
// しないよう、ラッパー（fieldClass = レイアウトのみ）と分離する。FormField が両者を内包。
export const labelClass = "font-mono text-xs uppercase tracking-[0.1em] text-muted";
export const fieldClass = "grid gap-1.5";
export const inputClass =
  "min-h-11 border border-neutral-300 bg-white px-3 py-2 text-base font-normal text-black outline-none transition-colors duration-150 focus:border-black";

// --- 副次テキスト ----------------------------------------------------------
export const mutedTextClass = "text-sm text-muted";

// --- 小バッジ（モノクロ。ステータス表示は StatusBadge コンポーネントを使う） --
export const badgeClass =
  "inline-flex items-center gap-1.5 border border-line bg-white px-3 py-1 font-mono text-xs uppercase tracking-[0.08em] text-black";

// --- 見出し（ドット系フォント。本文には使わない） --------------------------
export const sectionTitle = "font-dot text-2xl tracking-tight text-black sm:text-3xl";

// --- 罫線テーブル（工業製品の「銘板」風。SpecTable プリミティブが内包） ------
export const specTableClass = "w-full border-t border-line";
export const specRowClass =
  "flex items-baseline justify-between gap-4 border-b border-line py-3";

// --- 認証ページ（Login） ---------------------------------------------------
export const authFormClass = "grid gap-4 border border-line bg-white p-6";
