import type { ApiError } from "../lib/apiClient";

export type ButtonVariant = "primary" | "danger" | "ghost";

/** 画面共通のエラー状態。API エラー・一般 Error・エラーなしの 3 態。 */
export type AppError = ApiError | Error | null;
