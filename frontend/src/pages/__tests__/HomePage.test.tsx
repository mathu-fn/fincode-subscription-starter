import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HomePage } from "../HomePage";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  initFincodeUi: vi.fn(),
  mountFincodeUi: vi.fn(),
  unmountFincodeUi: vi.fn()
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
  tokenizeViaUi: vi.fn()
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: 1, email: "alice@example.com", name: "Alice", created_at: "2026-01-01T00:00:00Z" }
  })
}));

beforeEach(() => {
  mocks.apiFetch.mockImplementation((path: string) => {
    if (path === "/api/subscription") return Promise.resolve(null);
    if (path === "/api/subscription/plans") return Promise.resolve([]);
    if (path === "/api/subscription/cards") return Promise.resolve([]);
    if (path.startsWith("/api/subscription/history")) {
      return Promise.resolve({ data: [], page: 1, per_page: 10, total: 0 });
    }
    return Promise.resolve(null);
  });
  mocks.initFincodeUi.mockResolvedValue({ fincode: {}, ui: {} });
  mocks.mountFincodeUi.mockReset();
  mocks.unmountFincodeUi.mockReset();
});

describe("HomePage cards section", () => {
  it("hides the card form until the user clicks the add-card button, then mounts the fincode UI", async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.queryByText("新規カードを追加")).not.toBeInTheDocument();
    expect(document.getElementById("fincode-ui-mount")).not.toBeInTheDocument();
    expect(mocks.mountFincodeUi).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "カードを追加" }));

    expect(screen.getByText("新規カードを追加")).toBeInTheDocument();
    expect(screen.queryByText(/テストトークンを直接入力/)).not.toBeInTheDocument();
    expect(document.getElementById("fincode-ui-mount-form")).toBeInTheDocument();
    expect(document.getElementById("fincode-ui-mount")).toBeInTheDocument();

    await waitFor(() => {
      expect(mocks.mountFincodeUi).toHaveBeenCalledWith({}, "fincode-ui-mount");
    });

    await userEvent.click(screen.getByRole("button", { name: "閉じる" }));
    expect(screen.queryByText("新規カードを追加")).not.toBeInTheDocument();
    expect(document.getElementById("fincode-ui-mount")).not.toBeInTheDocument();
    expect(mocks.unmountFincodeUi).toHaveBeenCalled();
  });

  it("shows a loading overlay while the fincode UI initializes and hides it once mounted", async () => {
    let resolveInit: (bundle: { fincode: object; ui: object }) => void = () => {};
    mocks.initFincodeUi.mockReturnValue(
      new Promise((resolve) => {
        resolveInit = resolve;
      })
    );

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    await userEvent.click(screen.getByRole("button", { name: "カードを追加" }));

    // 初期化が resolve するまではオーバーレイが表示される
    expect(screen.getByRole("status")).toBeInTheDocument();

    resolveInit({ fincode: {}, ui: {} });

    // mount 完了でオーバーレイが消える
    await waitFor(() => {
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });
    expect(mocks.mountFincodeUi).toHaveBeenCalledWith({}, "fincode-ui-mount");
  });

  it("renders subscription and payment statuses as localized badges, with raw fallback for unknown values", async () => {
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path === "/api/subscription") {
        return Promise.resolve({
          id: 1,
          status: "active",
          plan_name: "スタンダード",
          plan_amount: 980,
          plan_interval: "month",
          cancelled_at: null,
          current_period_end: null,
          created_at: "2026-01-01T00:00:00Z"
        });
      }
      if (path === "/api/subscription/plans") return Promise.resolve([]);
      if (path === "/api/subscription/cards") return Promise.resolve([]);
      if (path.startsWith("/api/subscription/history")) {
        return Promise.resolve({
          data: [
            { id: 1, status: "succeeded", amount: 980, fincode_payment_id: "pay_1", charged_at: "2026-02-01T00:00:00Z" },
            { id: 2, status: "failed", amount: 980, fincode_payment_id: "pay_2", charged_at: "2026-03-01T00:00:00Z" },
            { id: 3, status: "authorized", amount: 980, fincode_payment_id: "pay_3", charged_at: "2026-04-01T00:00:00Z" }
          ],
          page: 1,
          per_page: 10,
          total: 3
        });
      }
      return Promise.resolve(null);
    });

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    // 契約状態は日本語ラベルになる（生の "active" は表示されない）。
    await waitFor(() => {
      expect(screen.getAllByText("契約中").length).toBeGreaterThan(0);
    });
    expect(screen.queryByText("active")).not.toBeInTheDocument();

    // 決済履歴の既知ステータスは日本語化される。
    expect(screen.getByText("成功")).toBeInTheDocument();
    expect(screen.getByText("失敗")).toBeInTheDocument();

    // 未知のステータスは生の文字列のままフォールバック表示する（値を落とさない）。
    expect(screen.getByText("authorized")).toBeInTheDocument();
  });

  it("confirms card deletion via the ConfirmDialog instead of window.confirm", async () => {
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path === "/api/subscription") return Promise.resolve(null);
      if (path === "/api/subscription/plans") return Promise.resolve([]);
      if (path === "/api/subscription/cards") {
        return Promise.resolve([
          {
            id: 77,
            brand: "VISA",
            last4: "4242",
            exp_month: 12,
            exp_year: 2030,
            created_at: "2026-01-01T00:00:00Z"
          }
        ]);
      }
      if (path.startsWith("/api/subscription/history")) {
        return Promise.resolve({ data: [], page: 1, per_page: 10, total: 0 });
      }
      return Promise.resolve(null);
    });

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    // カード一覧が読み込まれるまで待つ。この時点では削除ボタンは1つだけ。
    const deleteButton = await screen.findByRole("button", { name: "削除" });
    expect(mocks.apiFetch.mock.calls.some(([, opts]) => opts?.method === "DELETE")).toBe(false);

    // 削除ボタン押下でブラウザの confirm ではなく ConfirmDialog が開く。
    await userEvent.click(deleteButton);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("カードを削除しますか？")).toBeInTheDocument();

    // インラインの削除ボタンと名前が衝突するため、確定ボタンはダイアログ内にスコープして押す。
    await userEvent.click(within(dialog).getByRole("button", { name: "削除" }));

    await waitFor(() => {
      const deleteCall = mocks.apiFetch.mock.calls.find(
        ([path, opts]) => path === "/api/subscription/cards/77" && opts?.method === "DELETE"
      );
      expect(deleteCall).toBeTruthy();
    });
  });
});
