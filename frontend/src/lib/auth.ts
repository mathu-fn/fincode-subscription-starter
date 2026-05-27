/**
 * localStorage をバックエンドとする軽量なクライアントサイド認証ストア。
 *
 * 保存内容: JWT アクセストークン + /api/login が返すユーザーペイロード。
 * プロジェクトの README では XSS のトレードオフを明示的に許容しており、
 * 本番環境に移行する前に厳格な CSP を追加するよう利用者に求めている。
 */

const TOKEN_KEY = "fincode_jwt";
const USER_KEY = "fincode_user";

export type User = {
  id: number;
  email: string;
  name: string;
  created_at: string;
};

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage 利用不可（プライベートモード / ロックダウン / 無効化）。サイレントに無視。
  }
}

function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Storage 利用不可 — 削除するものがない。
  }
}

export function getToken(): string | null {
  return safeGetItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  safeSetItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  safeRemoveItem(TOKEN_KEY);
  safeRemoveItem(USER_KEY);
}

export function getUser(): User | null {
  const raw = safeGetItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setUser(user: User): void {
  safeSetItem(USER_KEY, JSON.stringify(user));
}
