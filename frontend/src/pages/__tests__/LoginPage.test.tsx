import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuthProvider } from "../../hooks/useAuth";
import { LoginPage } from "../LoginPage";

// GIS の実スクリプトは jsdom では動かず、実ボタンは Google 配信の iframe 内で
// クリックもできない。ローダーごとモックし、「捕捉した callback を普通のボタンの
// クリックで発火させる」形で credential の受け渡しをテストする。
vi.mock("../../lib/googleIdentity", () => {
  let capturedCallback: ((credential: string) => void) | null = null;
  return {
    initGoogleIdentity: vi.fn(async (onCredential: (credential: string) => void) => {
      capturedCallback = onCredential;
    }),
    renderGoogleButton: vi.fn(async (element: HTMLElement) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Google でログイン";
      button.addEventListener("click", () => capturedCallback?.("fake-google-credential"));
      element.appendChild(button);
    })
  };
});

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  it("sends the Google credential and stores the token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "test-token",
          token_type: "bearer",
          expires_at: "2026-01-01T00:00:00Z",
          user: { id: 1, email: "alice@example.com", name: "Alice", created_at: "2026-01-01T00:00:00Z" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    renderLoginPage();

    await userEvent.click(await screen.findByRole("button", { name: /Google でログイン/ }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/auth/google");
    expect(JSON.parse(init.body as string)).toEqual({ credential: "fake-google-credential" });
    expect(localStorage.getItem("fincode_jwt")).toBe("test-token");
  });

  it("shows an error message when the API rejects the login", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: { code: "invalid_google_token", message: "Google sign-in could not be verified." }
        }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    renderLoginPage();

    await userEvent.click(await screen.findByRole("button", { name: /Google でログイン/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Google ログインに失敗しました/);
    expect(localStorage.getItem("fincode_jwt")).toBeNull();
  });

  it("shows a conflict message when the email belongs to an existing account", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: { code: "email_already_registered", message: "This email is already registered." }
        }),
        { status: 409, headers: { "Content-Type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    renderLoginPage();

    await userEvent.click(await screen.findByRole("button", { name: /Google でログイン/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/既存のアカウントで使用されています/);
    expect(localStorage.getItem("fincode_jwt")).toBeNull();
  });
});
