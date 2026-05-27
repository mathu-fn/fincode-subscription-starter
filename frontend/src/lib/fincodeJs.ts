/**
 * 公式 fincode UI コンポーネントのローダーと薄いラッパー
 * (https://docs.fincode.jp/payment/ui_component/demo)。
 *
 * fincode SDK はカード番号・有効期限・CVC・名義人名の入力フィールドを
 * 制御下の iframe 内にレンダリングするため、生のカードデータが DOM に入ることはない。
 * 受け取るのはバックエンドへ転送するワンタイムトークンのみ。
 */

import { getCardToken, initFincode } from "@fincode/js";
import type { FincodeInstance, FincodeUI } from "@fincode/js";

export type FincodeUiBundle = { fincode: FincodeInstance; ui: FincodeUI };

let initPromise: Promise<FincodeUiBundle> | null = null;
let mountedElementId: string | null = null;

export function initFincodeUi(): Promise<FincodeUiBundle> {
  if (initPromise) return initPromise;

  const publicKey = import.meta.env.VITE_FINCODE_PUBLIC_KEY as string | undefined;
  if (!publicKey) {
    return Promise.reject(new Error("VITE_FINCODE_PUBLIC_KEY is not set."));
  }

  const isLiveMode =
    String(import.meta.env.VITE_FINCODE_LIVE_MODE ?? "").toLowerCase() === "true";

  initPromise = (async () => {
    const fincode = await initFincode({ publicKey, isLiveMode });
    const appearance = { layout: "vertical" as const, hidePayTimes: true };
    const ui = fincode.ui(appearance);
    // fincode.js v1 はここで "payment" を期待する（@fincode/js 1.1.0 の型定義は複数形の名前を列挙しているが）。
    ui.create("payment" as Parameters<FincodeUI["create"]>[0], appearance);
    return { fincode, ui };
  })().catch((err) => {
    initPromise = null;
    throw err;
  });

  return initPromise;
}

export function mountFincodeUi(ui: FincodeUI, elementId: string, width: string = "400"): void {
  if (mountedElementId === elementId) return;
  ui.mount(elementId, width);
  mountedElementId = elementId;
}

export function unmountFincodeUi(ui: FincodeUI | null | undefined): void {
  if (!ui) return;
  const maybeUnmount = (ui as { unmount?: () => void }).unmount;
  if (typeof maybeUnmount === "function") {
    try {
      maybeUnmount.call(ui);
    } catch {
      // 無視する — ベストエフォートのクリーンアップ
    }
  }
  mountedElementId = null;
}

export async function tokenizeViaUi(fincode: FincodeInstance, ui: FincodeUI): Promise<string> {
  const result = await getCardToken({ fincode, ui, number: "1" });
  const token = result?.list?.[0]?.token;
  if (!token) {
    throw new Error("fincode UI did not return a token.");
  }
  return token;
}
