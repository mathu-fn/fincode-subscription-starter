import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mockApiFetch } from "../../test/mockApi";
import { renderHomePage } from "../../test/renderHomePage";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  initFincodeUi: vi.fn(),
  mountFincodeUi: vi.fn(),
  unmountFincodeUi: vi.fn(),
  tokenizeViaUi: vi.fn()
}));

vi.mock("../../lib/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../../lib/apiClient")>("../../lib/apiClient");
  return {
    ...actual,
    apiFetch: mocks.apiFetch
  };
});

vi.mock("../../lib/fincodeJs", () => ({
  initFincodeUi: mocks.initFincodeUi,
  mountFincodeUi: mocks.mountFincodeUi,
  unmountFincodeUi: mocks.unmountFincodeUi,
  tokenizeViaUi: mocks.tokenizeViaUi
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: 1, email: "alice@example.com", name: "Alice", created_at: "2026-01-01T00:00:00Z" }
  })
}));

beforeEach(() => {
  // VITE_FINCODE_MODE=mock を有効化（isFincodeMockMode() が true を返す）。
  vi.stubEnv("VITE_FINCODE_MODE", "mock");
  mocks.apiFetch.mockImplementation(mockApiFetch());
  mocks.initFincodeUi.mockReset();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("HomePage cards section (mock mode)", () => {
  it("shows a direct token input instead of the fincode UI and never loads fincode.js", async () => {
    renderHomePage();

    await userEvent.click(screen.getByRole("button", { name: "カードを追加" }));

    // モック用の直接入力フォームが出て、fincode.js のマウント先は出ない。
    expect(screen.getByText("テストトークンを直接入力")).toBeInTheDocument();
    expect(document.getElementById("fincode-ui-mount")).not.toBeInTheDocument();
    expect(mocks.initFincodeUi).not.toHaveBeenCalled();
  });

  it("posts the entered token to the cards endpoint without calling fincode.js tokenization", async () => {
    renderHomePage();

    await userEvent.click(screen.getByRole("button", { name: "カードを追加" }));
    await userEvent.click(screen.getByRole("button", { name: "カードを追加" }));

    expect(mocks.tokenizeViaUi).not.toHaveBeenCalled();
    const cardCall = mocks.apiFetch.mock.calls.find(
      ([path, opts]) => path === "/api/subscription/cards" && opts?.method === "POST"
    );
    expect(cardCall).toBeTruthy();
    expect(JSON.parse(cardCall![1].body as string)).toEqual({ token: "tok_mock_visa" });
  });
});
