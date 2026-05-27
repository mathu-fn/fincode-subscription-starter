import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuthProvider } from "../../hooks/useAuth";
import { LoginPage } from "../LoginPage";

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("LoginPage", () => {
  it("submits the credentials and stores the token", async () => {
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

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/メールアドレス/i), "alice@example.com");
    await userEvent.type(screen.getByLabelText(/パスワード/i), "supersecret");
    await userEvent.click(screen.getByRole("button", { name: /ログイン/ }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem("fincode_jwt")).toBe("test-token");
  });

  it("shows an error message when the API rejects the login", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: { code: "invalid_credentials", message: "Invalid email or password." }
        }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/メールアドレス/i), "wrong@example.com");
    await userEvent.type(screen.getByLabelText(/パスワード/i), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /ログイン/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/メールアドレスかパスワードが正しくありません/);
    expect(localStorage.getItem("fincode_jwt")).toBeNull();
  });
});
