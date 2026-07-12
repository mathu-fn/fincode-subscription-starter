import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildCard, buildHistoryItem, buildHistoryPage, buildPlan, buildSubscription } from "../../test/fixtures";
import { mockApiFetch } from "../../test/mockApi";
import { renderHomePage } from "../../test/renderHomePage";

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
  mocks.apiFetch.mockImplementation(mockApiFetch());
  mocks.initFincodeUi.mockResolvedValue({ fincode: {}, ui: {} });
  mocks.mountFincodeUi.mockReset();
  mocks.unmountFincodeUi.mockReset();
});

describe("HomePage cards section", () => {
  it("hides the card form until the user clicks the add-card button, then mounts the fincode UI", async () => {
    renderHomePage();

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

    renderHomePage();

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
    mocks.apiFetch.mockImplementation(
      mockApiFetch({
        "/api/subscription": buildSubscription({
          plan_name: "スタンダード",
          plan_amount: 980
        }),
        "/api/subscription/history": buildHistoryPage([
          buildHistoryItem({ id: 1, status: "succeeded", fincode_payment_id: "pay_1", charged_at: "2026-02-01T00:00:00Z" }),
          buildHistoryItem({ id: 2, status: "failed", fincode_payment_id: "pay_2", charged_at: "2026-03-01T00:00:00Z" }),
          buildHistoryItem({ id: 3, status: "authorized", fincode_payment_id: "pay_3", charged_at: "2026-04-01T00:00:00Z" })
        ])
      })
    );

    renderHomePage();

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

  it("shows cancel-at-period-end state and blocks further cancellation or plan changes", async () => {
    mocks.apiFetch.mockImplementation(
      mockApiFetch({
        "/api/subscription": buildSubscription({
          cancelled_at: "2026-01-15T00:00:00Z",
          current_period_end: "2026-02-01T00:00:00Z",
          cancel_at_period_end: true
        }),
        "/api/subscription/plans": [
          buildPlan(),
          buildPlan({ fincode_plan_id: "plan_mock_pro", name: "プロ", amount: 1500 })
        ]
      })
    );

    renderHomePage();

    await waitFor(() => {
      expect(screen.getAllByText("解約予約中").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("利用可能期限")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "解約する" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "解約予約中" })).toBeDisabled();
  });

  it("confirms card deletion via the ConfirmDialog instead of window.confirm", async () => {
    mocks.apiFetch.mockImplementation(
      mockApiFetch({
        "/api/subscription/cards": [buildCard()]
      })
    );

    renderHomePage();

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

  it("treats an unpaid subscription as the current subscription (badge, plan change button, cancel button)", async () => {
    mocks.apiFetch.mockImplementation(
      mockApiFetch({
        "/api/subscription": buildSubscription({ status: "unpaid" }),
        "/api/subscription/plans": [
          buildPlan(),
          buildPlan({ fincode_plan_id: "plan_mock_pro", name: "プロ", amount: 1500 })
        ]
      })
    );

    renderHomePage();

    // 未払いバッジと案内文が表示される（サマリーと契約セクションの複数箇所に出る）。
    await waitFor(() => {
      expect(screen.getAllByText("未払い").length).toBeGreaterThan(0);
    });
    expect(screen.getByText(/お支払いが確認できませんでした/)).toBeInTheDocument();

    // 新規契約（POST は 409 になる）ではなくプラン変更ボタンになる。
    expect(screen.getByRole("button", { name: "このプランに変更" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "このプランを契約" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "現在のプラン" })).toBeDisabled();

    // 未払い中でも解約はできる。
    expect(screen.getByRole("button", { name: "解約する" })).toBeInTheDocument();
  });

  it("uses the plan change endpoint when an active subscription already exists", async () => {
    mocks.apiFetch.mockImplementation(
      mockApiFetch({
        "/api/subscription": (_path: string, init?: RequestInit) =>
          init?.method === "PATCH"
            ? buildSubscription({ fincode_plan_id: "plan_mock_pro", plan_name: "プロ", plan_amount: 1500 })
            : buildSubscription(),
        "/api/subscription/plans": [
          buildPlan(),
          buildPlan({ fincode_plan_id: "plan_mock_pro", name: "プロ", amount: 1500 })
        ]
      })
    );

    renderHomePage();

    await userEvent.click(await screen.findByRole("button", { name: "このプランに変更" }));

    await waitFor(() => {
      const changeCall = mocks.apiFetch.mock.calls.find(
        ([path, opts]) => path === "/api/subscription" && opts?.method === "PATCH"
      );
      expect(changeCall).toBeTruthy();
      expect(JSON.parse(String(changeCall?.[1]?.body))).toEqual({
        fincode_plan_id: "plan_mock_pro"
      });
    });
  });
});
