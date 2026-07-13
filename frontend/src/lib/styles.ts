// 複数ページで共有する Tailwind クラス文字列をここに集約する。
// ページ固有のものも、重複を避けるため元の変数名のまま再エクスポートする。
// 注意: cardClass はページごとに padding が異なる（HomePage p-4 / LandingPage p-6）ため、
// 各ページにローカル定義を残し、ここでは共通化しない。

// HomePage
export const pageClass = "mx-auto grid max-w-5xl gap-5";
export const sectionClass = "grid scroll-mt-24 gap-3";
export const summaryCardClass =
  "grid min-h-28 gap-1.5 border border-sky-200 bg-white p-4";
export const primaryLinkClass =
  "inline-flex min-h-11 items-center justify-center border border-sky-600 bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2";

// フォーム入力（HomePage の支払いカード選択などで共通）
export const labelClass = "grid gap-1.5 text-sm font-semibold text-slate-700";
export const inputClass =
  "min-h-11 border border-sky-200 bg-white px-3 py-2 text-base font-normal text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-200";

// LandingPage
export const badgeClass =
  "inline-flex items-center gap-1.5 border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700";
export const primaryBtn =
  "inline-flex min-h-11 items-center justify-center border border-sky-600 bg-sky-500 px-6 py-3 text-sm font-semibold text-white hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2";
export const secondaryBtn =
  "inline-flex min-h-11 items-center justify-center border border-sky-600 bg-white px-6 py-3 text-sm font-semibold text-sky-700 hover:bg-sky-50 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2";
export const sectionTitle = "text-2xl font-bold text-sky-950 sm:text-3xl";
export const codeChip = "bg-sky-50 px-1.5 py-0.5 font-mono text-[0.85em] text-sky-800";

// 認証ページ（Login）
export const authFormClass =
  "grid gap-4 border border-sky-200 bg-white p-6";
