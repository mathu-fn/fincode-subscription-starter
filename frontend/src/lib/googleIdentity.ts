/**
 * Google Identity Services (GIS) のローダーと薄いラッパー
 * (https://developers.google.com/identity/gsi/web)。
 *
 * GIS はログインボタンを Google 配信の iframe 内にレンダリングし、認証完了時に
 * callback へ ID トークン（credential）を渡す。パスワードや Google のセッション
 * 情報がアプリの DOM に入ることはなく、受け取った credential をバックエンドの
 * POST /api/auth/google へ転送するだけでよい。credential は保存しない。
 */

/// <reference types="google.accounts" />

const GSI_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

declare global {
  interface Window {
    google?: typeof google;
  }
}

let loadPromise: Promise<typeof google.accounts.id> | null = null;

function loadGsi(): Promise<typeof google.accounts.id> {
  if (loadPromise) return loadPromise;

  loadPromise = new Promise<typeof google.accounts.id>((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve(window.google.accounts.id);
      return;
    }
    const script = document.createElement("script");
    script.src = GSI_SCRIPT_SRC;
    script.async = true;
    script.onload = () => {
      if (window.google?.accounts?.id) {
        resolve(window.google.accounts.id);
      } else {
        reject(new Error("Google Identity Services did not initialize."));
      }
    };
    script.onerror = () => reject(new Error("Failed to load Google Identity Services."));
    document.head.appendChild(script);
  }).catch((err: unknown) => {
    // 失敗時はリセットして次回の呼び出しで再試行できるようにする。
    loadPromise = null;
    throw err;
  });

  return loadPromise;
}

export async function initGoogleIdentity(
  onCredential: (credential: string) => void
): Promise<void> {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
  if (!clientId) {
    throw new Error("VITE_GOOGLE_CLIENT_ID is not set.");
  }
  const id = await loadGsi();
  id.initialize({
    client_id: clientId,
    callback: (response: google.accounts.id.CredentialResponse) =>
      onCredential(response.credential),
    // One Tap の自動サインインは使わない（意図しないログインとループを防ぐ）。
    auto_select: false
  });
}

export async function renderGoogleButton(element: HTMLElement): Promise<void> {
  const id = await loadGsi();
  id.renderButton(element, {
    type: "standard",
    theme: "outline",
    size: "large",
    text: "signin_with",
    width: 320
  });
}
