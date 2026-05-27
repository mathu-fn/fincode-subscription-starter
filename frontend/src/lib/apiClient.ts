/**
 * React アプリが FastAPI バックエンドと通信する単一の窓口。
 *
 * - API ベース URL を先頭に付加する
 * - localStorage から JWT を添付する
 * - 401 の場合はトークンをクリアし、ルートガードが /login へリダイレクトできるよう
 *   エラーを伝播させる
 * - バックエンドの安定したエラーエンベロープを ``ApiError`` にデコードする
 */

import { clearToken, getToken } from "./auth";

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

export type ApiErrorBody =
  | { detail: { code: string; message: string } }
  | { detail: Array<{ loc: Array<string | number>; msg: string; type: string }> }
  | { detail: string };

export class ApiError extends Error {
  status: number;
  code: string;
  body: ApiErrorBody | null;

  constructor(status: number, code: string, message: string, body: ApiErrorBody | null) {
    super(message);
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    let code = `http_${response.status}`;
    let message = `Request failed with status ${response.status}`;
    if (body && typeof body === "object" && "detail" in (body as Record<string, unknown>)) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "object" && detail !== null && "code" in detail && "message" in detail) {
        code = (detail as { code: string }).code;
        message = (detail as { message: string }).message;
      } else if (Array.isArray(detail)) {
        message = detail.map((d) => (typeof d === "object" && d && "msg" in d ? (d as { msg: string }).msg : String(d))).join(", ");
        code = "validation_error";
      } else if (typeof detail === "string") {
        message = detail;
      }
    }
    if (response.status === 401) {
      clearToken();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("fincode:auth-cleared"));
      }
    }
    throw new ApiError(response.status, code, message, body as ApiErrorBody | null);
  }

  return body as T;
}

export const apiBaseUrl = BASE_URL;
